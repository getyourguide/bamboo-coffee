# Bamboo Coffee

Bamboo Coffee is the opensource version of the tool we use at GetYourGuide to pair random people for having a virtual coffee break together during this work-from-home season.

From the list of employees, the program does run `NUMBER_OF_TRIALS` simulations. Each time it generates a random subsets of `GROUP_SIZE` employees, then calculates the diversity score for this simulation based on the criteria in `OPTIMIZED_FEATURE`. At the end, the simulation with the highest diversity score is chosen. Each subset of employees is sent an email invitation to get together for a coffee break.

# Setup
The following prerequisites are assumed for the setup:

- The HR system, from which employees data is pulled, is BambooHR. If yours is different, make the change in method `load_df()`

- The employee data has the fields: 'displayName', 'workEmail', 'department', 'location', 'jobTitle', 'firstName'

- Emails are sent via SMTP protocol.

# Configuration
The provided config file template [config_template.txt](./config_template.txt) includes a list of expected configuration options.

Section `GROUPING`:
- FEATURES: comma-separated (without space) list of employees data fields
- WHITELIST_LOCATIONS: comma-separated (without space) list of office locations from which employees are invited (we use this to only include offices from a specific timezone)
- OPT_OUT_EMPLOYEES:comma-separated (without space) email list of employees to be excluded from invitations
- GROUP_SIZE: how many people should be in a group
- OPTIMIZED_FEATURE: the feature for which the diversity is optimized. 
  - 'department' means we optimize to have people from different departments in each group.
  - 'location' means we optimize to have people from different office locations in each group.
- NUMBER_OF_TRIALS: how many times we want to run the simulations

Sections `BAMBOO` and `SMTP` contain configuration related to BambooHR and SMTP.

# Run
Install python dependencies:
```
pip3 install -r requirements.txt
```

Provide your own configuration by copying the template config file and adjusting it to your needs:
```
cp config_template.txt config.txt
```

Make sure you have the following configured properly:
- `WHITELIST_LOCATIONS` (needs to match the values from your BambooHR, otherwise no pairings are generated)
- `APIKEY` in `BAMBOO` section (get it from your BambooHR portal)
- `SUBDOMAIN` in `BAMBOO` section (use the part coming before .bamboohr.com)
- `SMTP` section (to allow sending of emails)


Run and print the result to stdout, no emails sent:
```
python3 bamboo_coffee.py
```

Run and send only 1 invitation email to the provided recipient:
```
python3 bamboo_coffee.py test abc@example.com
```

Run and send invitation emails to everyone
```
python3 bamboo_coffee.py send
```

# Security

For security issues please contact [security@getyourguide.com](mailto:security@getyourguide.com).

# Legal

Copyright 2021 GetYourGuide GmbH.

BambooCoffee is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
