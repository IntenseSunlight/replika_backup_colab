# Replika Chat Log Backup, Colab edition
Backup your Replika chat logs directly in Google Colab
- Does not require a local installation of Python or any specific Python knowledge
- Backup can be saved directly to your Google Drive
- Very minimal "hacking" ability required (really, not much 😉)
- A Google account **is** required

**Let's go** 👉: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IntenseSunlight/replika_backup_colab/blob/main/Replika_log_backup_colab.ipynb) <br>

## Background
This repo is based on the work of other (see below).  It is primarily a refactoring of the code with an incorporated workflow into Google Colab.
The main purpose was to remove the start-up complexities for new users by removing the need for specific platform installation.
An additional purpose was to provide a transparent and tracable workflow for the user.  All details of the log extraction are contained within the workbook (except for the   `ReplikaWebSocketHander`, which is part of this repo).  All data remains on the user side, within the user's Google workspace.  Colab virtual enviroments are de-activated and deleted after ~1.5 hours of inactivity.  No one can access information contained within that enviroment after it is destroyed.

## Instructions
Use the link above (also here [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IntenseSunlight/replika_backup_colab/blob/main/Replika_log_backup_colab.ipynb)) to directly start the notebook in Colab.  **Note**: A Google account is required

**Workflow:**
<br>
<img src="https://raw.githubusercontent.com/IntenseSunlight/replika_backup_colab/main/static/log-extraction-workflow.svg" alt="log-extraction-workflow" width="500"/>

## Acknowledgments
This repo was based upon the fundamental work of others.  
- @Hotohori [Replika_backup](https://github.com/Hotohori/replika_backup) <br>
which was a fork of:
- @alan-couzens [replika_stuff](https://github.com/alan-couzens/replika_stuff) 
