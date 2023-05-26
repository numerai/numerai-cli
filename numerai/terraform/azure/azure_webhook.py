# TODO: to be edited, check how to install req, and get external env variables from TF
# https://www.youtube.com/watch?v=P-tZ28RhYE4&ab_channel=TomHa

import azure.functions as func
import logging
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.identity import DefaultAzureCredential
import os

# Remember to create a .env file in the same directory as this file to store environment variable "AZURE_SUBSCRIPTION_ID"
#from dotenv import load_dotenv
#load_dotenv()

# This function will be triggered by a GET or POST request (defined in function.json)
def main(predict: func.HttpRequest) -> func.HttpResponse:
    
    logging.info('Python HTTP trigger function processed a request.')
    
    # Pass the necessary credential to the client
    client = ContainerInstanceManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"]) # loaded from .env within azure_trigger_function folder
    
    # Start the container instance
    response = client.container_groups.begin_start(
        resource_group_name=os.environ["AZURE_RG_NAME"],
        container_group_name=os.environ["AZURE_CRG_NAME"],
        ).result()
    
    return func.HttpResponse(f"This HTTP triggered function executed successfully.",status_code=200)
