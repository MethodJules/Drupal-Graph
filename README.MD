# Jigsaw.Graph Architecture #

This repository serves as a starting point if you want to integrate a knowledge graph into your community portal which is based on
the CMS Drupal.

## What do I need? ##
You need a running Drupal 8 or 9 instance and some space on your server hard disk. You will also need a working Docker- and Docker Compose-Environment.

## How can I start ##
Copy the folder "nlp_search" into the Drupal modules folder. We recommend to create an extra folder with the name "custom" (if there is not already one) as parent folder.
Activate the module in the administration panel of Drupal. As you will probably know, clear the cache!
Start the docker-compose file by running "docker-compose up". We recommend to run this command without detached mode to see if all has worked properly. For example don't worry about long loading times with the python container. We set up a delay so the Neo4j container will come up first.
Start the nltkDownload.py script. You only have to repeat this step if your container was stopped. After that goto your Drupal Site under admin/config/search/nlpsearch.
Enter the data (Serveradress and so on). Configure which content types and fields need to be indexed. After indexing start the nlpProcess.py script. We recommend to create a cron job which will run this script ever 24 hours. Then you can lean back and let the machine do the work.

## Contact ##
If you have any questions feel free to create new issues at this repository. Best regards Julien Hofer and Marco Di Maria.


