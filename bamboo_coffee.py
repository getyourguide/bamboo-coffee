from PyBambooHR.PyBambooHR import PyBambooHR
import csv
import os
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import statistics
import sys
import jinja2
import itertools
import configparser


def load_df():
    EMPLOYEES_CSV = config['DEFAULT']['EMPLOYEES_CSV']
    CSV_DELIMITER = config['DEFAULT']['CSV_DELIMITER']
    FEATURES = config['GROUPING']['FEATURES'].split(',')
    BAMBOOHR_APIKEY = config['BAMBOO']['APIKEY']
    BAMBOOHR_SUBDOMAIN = config['BAMBOO']['SUBDOMAIN']
    if not os.path.exists(EMPLOYEES_CSV):
        # Load employee info from BambooHR into a Pandas data frame
        employees = PyBambooHR(
            subdomain=BAMBOOHR_SUBDOMAIN,
            api_key=BAMBOOHR_APIKEY,
        ).get_employee_directory()
        employees_list = [[e[v] for v in FEATURES] for e in employees]
        with open(EMPLOYEES_CSV, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file, delimiter=CSV_DELIMITER)
            for employee in employees_list:
                writer.writerow(employee)
    else:
        print("Found existing employees data. Remove it manually if you want to refresh and get the latest data.")

    df = pd.read_csv(
        EMPLOYEES_CSV,
        names=['name', 'email', 'department', 'city', 'title', 'firstName'],
        sep=CSV_DELIMITER
    ).dropna()

    return df


def partition(df, group_size, feature, group_constraints, trials=100000):
    """Takes a dataframe and returns a list of list of indices
       such that we have m+n disjoint sublists with m*4+n*3=len(list)
       and m being as great as possible (m,n being natural numbers
       greater than 0) and diversity of "feature" within sublists
       is high: samples _trials_ partitions and takes the best one
       with respect to _diversity_ score
    """

    def calculateDiversity(partition):
        partitions = [list(map(lambda member: member[1], group)) for group in partition]
        partitionsDiversity = list(map(lambda group: (len(set(group)) * 1.0) / len(group), partitions))
        return statistics.mean(partitionsDiversity)

    def find_suitable_group_sizes(total):
        i = 0
        while i <= total and (total - i) % group_size != 0:
            i += group_size_minus
        if i <= total:
            num_normal_group_size = int((total - i)/group_size)
            num_minus_group_size = int(i/group_size_minus)
            return (num_normal_group_size, num_minus_group_size, (num_normal_group_size*group_size)%total)
        else:
            raise Exception(f"Not able to find suitable group size {group_size} for the total number of {total}")


    num_indices = df.shape[0]

    if num_indices <= (group_size + 1):
        return [list(df.index)]
    else:
        group_size_minus = group_size - 1
        num_normal_group_size, num_minus_group_size, offset = find_suitable_group_sizes(num_indices)

        indexed = list(zip(df.index, df[feature]))

        bestScore = -1

        for _ in range(trials):
            random.shuffle(indexed)
            partition = [indexed[i*group_size : (i+1)*group_size] for i in range(0, num_normal_group_size)] + \
                        [indexed[offset+(i*group_size_minus) : offset+(i+1)*group_size_minus] for i in range(0, num_minus_group_size)]

            if group_constraints is not None:
                partition_emails = [set(map(lambda member: df.loc[member[0]]['email'], group)) for group in partition]
                set_group_constraints = [set(c) for c in group_constraints]
                group_constraint_pairs = list(itertools.product(partition_emails, set_group_constraints))
                if any(group.issuperset(constraint) for group, constraint in group_constraint_pairs):
                    continue

            currentScore = calculateDiversity(partition)
            if currentScore > bestScore:
                bestScore = currentScore
                bestPartition = partition

        return [list(map(lambda member: member[0], group)) for group in bestPartition]


def create_group_emails(group, df, sender, title, body_template):
    ret_list = []
    organiser_id = random.randrange(len(group))
    organiser = df.loc[group[organiser_id]]['name']
    for index in group:
        name = df.loc[index]['firstName']
        email = df.loc[index]['email']
        buddy_info = []
        buddy_emails = []
        for buddy_index in group:
            if index != buddy_index:
                buddy_info.append([
                    df.loc[buddy_index]['name'],
                    df.loc[buddy_index]['department'],
                    df.loc[buddy_index]['title'],
                    df.loc[buddy_index]['city']])
                buddy_emails.append(df.loc[buddy_index]['email'])
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = email
        msg['reply-to'] = ', '.join(buddy_emails)
        msg['Subject'] = "{}, {}".format(name, title)
        body = body_template.render(name=name,
                                    buddy_info=buddy_info,
                                    group=group,
                                    index=index,
                                    organiser_id=organiser_id,
                                    organiser=organiser)
        msg.attach(MIMEText(body, 'plain'))
        ret_list.append([msg, email])
    return ret_list


def generate_and_send_emails(groups, df, body_template, test_recipient=None):
    SMTP_SENDER = config['SMTP']['SENDER']
    SMTP_SUBJECT = config['SMTP']['SUBJECT']
    SMTP_HOST = config['SMTP']['HOST']
    SMTP_PORT = int(config['SMTP']['PORT'])
    SMTP_USER = config['SMTP']['USER']
    SMTP_PASSWORD = config['SMTP']['PASSWORD']
    with smtplib.SMTP(host=SMTP_HOST, port=SMTP_PORT) as smtp:
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        for group in groups:
            group_emails = create_group_emails(group, df, SMTP_SENDER, SMTP_SUBJECT, body_template)
            for email in group_emails:
                text = email[0].as_string()
                recipient = email[1]
                if test_recipient is None:
                    smtp.sendmail(SMTP_SENDER, recipient, text)
                elif recipient == test_recipient:
                    smtp.sendmail(SMTP_SENDER, test_recipient, text)


def debug_send_emails(groups, df):
    for group in groups:
        print(f"{'city':>15}{'department':>45}{'title':>60}{'name':>60}")
        for index in group:
            print(f"{df.loc[index]['city']:>15}{df.loc[index]['department']:>45}{df.loc[index]['title']:>60}{df.loc[index]['name']:>60}")
        print("\n***************************************\n")


def run(group_size, filterFunc, template_filename, diversity_feature, group_constraints=None):
    test_recepient = None
    send_emails = sys.argv[-1] == 'send'
    test_emails = len(sys.argv) == 3 and sys.argv[-2] == 'test'
    if send_emails:
        print('Sending real emails')
    elif test_emails:
        test_recepient = sys.argv[-1]
        print('Sending test emails to {}'.format(test_recepient))
    else:
        print('Printing example emails')

    df = load_df()
    filtered_df = df.loc[filterFunc(df), :]
    NUMBER_OF_TRIALS = int(config['GROUPING']['NUMBER_OF_TRIALS'])
    groups = partition(filtered_df, group_size, diversity_feature, group_constraints, NUMBER_OF_TRIALS)

    if send_emails or test_emails:
        with open(template_filename, 'r') as f:
            body_template = jinja2.Template(f.read())
            generate_and_send_emails(groups, filtered_df, body_template, test_recepient)
    else:
        debug_send_emails(groups, filtered_df)


def filter_bamboo_coffee(df):
    WHITELIST_LOCATIONS = config['GROUPING']['WHITELIST_LOCATIONS'].split(',')
    OPT_OUT_EMPLOYEES = config['GROUPING']['OPT_OUT_EMPLOYEES'].split(',')
    return df['city'].isin(WHITELIST_LOCATIONS) & ~df['email'].isin(OPT_OUT_EMPLOYEES)


if __name__ == '__main__':
    global config
    config = configparser.ConfigParser()
    config.read('config.txt')
    GROUP_SIZE = int(config['GROUPING']['GROUP_SIZE'])
    OPTIMIZED_FEATURE = config['GROUPING']['OPTIMIZED_FEATURE']
    run(GROUP_SIZE, filter_bamboo_coffee, 'bamboo_coffee.j2', OPTIMIZED_FEATURE)
