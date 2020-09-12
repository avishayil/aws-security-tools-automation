# Automatic provisioning of security tools

## Deployment instructions

- Install python dependencies (currently tested on python 3): `pip install -r requirements.txt`
- Copy the example configuration files on your workspace:
  - `cp enable.example.csv enable.csv`
  - `cp config.example.yml config.yml`
- On each account, apply the trust cloudformations from each of the subfolders:
  - `EnableConfig.yaml`
  - `EnableGuardDuty.yaml`
  - `EnableSecurityHub.yaml`
  - `EnableDetective.yaml`

- Put the regions, master account and bucket configuration into `config.yml` file
- Supply the child accounts information with root account email on `enable.csv` file
- Run the `run.sh` script while your'e in the context of your master account, which is capable of assuming the roles you defined earlier