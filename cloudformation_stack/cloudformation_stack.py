import logging
from boto3 import client

class CloudFormationStack:

    # CloudFormationStack Constructor
    # logger: Logger object
    #
    # Returns: CloudFormationStack object
    # Raises: None
    def __init__(self, logger: logging.Logger, cloudformation_client: client):
        
        self.logger = logger
        self.cloudformation_client = cloudformation_client

    # get_stack_outputs: Retrieve CloudFormation Stack outputs from a specific stack using the stack physical resource ID, returns the specific stack outputs as `dict`.
    def get_stack_outputs(self, stack_physical_resource_id: str) -> dict:
        
        describe_stacks_response = self.cloudformation_client.describe_stacks(
            StackName=stack_physical_resource_id
        )

        self.logger.debug('Describe Stack Response - ' + str(describe_stacks_response))

        stack_output = {}

        if 'Outputs' in describe_stacks_response['Stacks'][0]:

            for output in describe_stacks_response['Stacks'][0]['Outputs']:

                stack_output.update({ 
                    output['OutputKey']: output['OutputValue']
                })

        self.logger.debug('Stack Output - ' + str(stack_output))

        return { stack_physical_resource_id: stack_output }  