from os import environ, getcwd, listdir
import re
import logging
import traceback
import json

# The ConfigMap - Mapping between runtime environment variable keys and JSON Config keys. Will need to append 'INPUT_' when looking to map within GitHub Actions environment
ConfigKeyValuePair = {
    'JIRA_CLOUD_URL': 'jira.cloud_url',
    'JIRA_PROJECT_KEY': 'jira.project_key',
    'JIRA_AUTH_EMAIL': 'jira.auth_email',
    'JIRA_API_TOKEN': 'jira.api_token',
    'JIRA_DEFAULT_ISSUE_LABELS': 'jira.default_issue_labels',
    'JIRA_ENABLED': 'jira.enabled'
}

# ConfigHandler: class to handle configuration file and environment variables
class ConfigHandler():

    # ConfigHandler Constructor
    # jira_cloud_url: str
    # jira_project_key: str
    # jira_auth_email: str
    # jira_api_token: str
    # jira_default_issue_labels: list
    # jira_enabled: bool
    #
    # Returns: ConfigHandler object
    # Raises: None
    def __init__(self, logger: logging.Logger):

        # Create a JSON Config parser
        self.logger = logger
        self.jira_cloud_url = self.jira_project_key = self.jira_auth_email = self.jira_api_token = ''
        self.jira_default_issue_labels = []
        self.jira_enabled = False
        self.config = self.build_config()
        self.required_fields = ['jira.cloud_url', 'jira.project_key', 'jira.auth_email', 'jira.api_token']

    # Get Boolean
    def get_boolean(self, key: str):
        return True if str(key).lower() == 'true' and key != '' else False

    # Build the Config object
    def build_config(self) -> dict:
        return {
            'jira': {
                'cloud_url': self.jira_cloud_url,
                'project_key': self.jira_project_key,
                'auth_email': self.jira_auth_email,
                'api_token': self.jira_api_token,
                'default_issue_labels': self.jira_default_issue_labels,
                'enabled': False
            }
        }

    # Load the config.json file from the current working directory, or from the GITHUB_WORKSPACE environment variable if running inside GitHub Actions
    def __load_config_file(self) -> dict:

        try:
            config = {}
            local_directory = getcwd()

            if 'GITHUB_ACTIONS' in environ.keys():

                self.logger.debug('Running inside GitHub Actions')
                local_directory = environ.get('GITHUB_WORKSPACE')

            for file in listdir(local_directory):

                if file == 'config.json':

                    with open('config.json', 'r+') as config_file:

                        config = json.loads(config_file.read())

                        self.logger.debug("JSON Config - " + str(config))

            return config if config else self.config
        
        except Exception as e:
            self.logger.error('Error loading config.json file: ' + str(traceback.print_tb(e.__traceback__)))

    # Load the config.json file from environment variables instead if running inside GitHub Actions. Environment variables override config.json values to enable CI workflows.
    def __load_config_env(self) -> dict:

        try:
            config = {}

            temp_list = []
            for config_key, config_value in ConfigKeyValuePair.items():
        
                if 'GITHUB_ACTIONS' in environ.keys():
                        if environ['GITHUB_ACTIONS']:
                            config_key = 'INPUT_' + config_key

                if config_key in environ.keys():
                    self.logger.debug('Config found within environment variables - ' + str(config_key) + ' - ' + str(config_value))
                    temp_list.append(config_value)

            self.logger.debug('ConfigMap JSON key values found within environment variables - ' + str(temp_list))

            unique_parent_list = []
            for item in temp_list:
                if item.split('.')[0] not in unique_parent_list:
                    unique_parent_list.append(item.split('.')[0])

            self.logger.debug('Parent config attributes found within environment variables - ' + str(unique_parent_list))

            for parent_item in unique_parent_list:

                temp_config_dict = {}
                for list_item in [x for x in temp_list if re.match(parent_item+'.*', x)]:

                    if 'GITHUB_ACTIONS' in environ.keys():
                        if environ['GITHUB_ACTIONS']:
                            list_item = 'INPUT_' + list_item

                    self.logger.debug('Config `' + str(list_item) + '` within parent `' + str(parent_item) + '` - ' + str(environ[list_item.replace('.', '_').upper()]))

                    item_path = list_item.split('.')
                    for item in reversed(item_path):
                        
                        if 'GITHUB_ACTIONS' in environ.keys():
                            if environ['GITHUB_ACTIONS']:
                                if list_item == 'INPUT_jira.default_issue_labels':
                                    temp_config_dict.update({
                                        item: environ[list_item.replace('.', '_').upper()].split(',')
                                    })
                                else:
                                    if list_item in ['INPUT_jira.enabled']:
                                        temp_config_dict.update({
                                            item: self.get_boolean(environ[list_item.replace('.', '_').upper()])
                                        })
                                    else:
                                        temp_config_dict.update({
                                            item: environ[list_item.replace('.', '_').upper()]
                                        })
                                config.update({list_item.split('.')[0].replace('INPUT_',''): temp_config_dict})
                                break
                        else:
                            if list_item == 'jira.default_issue_labels':
                                temp_config_dict.update({
                                    item: environ[list_item.replace('.', '_').upper()].split(',')
                                })
                            else:
                                if list_item in ['jira.enabled']:
                                    temp_config_dict.update({
                                        item: self.get_boolean(environ[list_item.replace('.', '_').upper()])
                                    })
                                else:
                                    temp_config_dict.update({
                                        item: environ[list_item.replace('.', '_').upper()]
                                    })
                            config.update({list_item.split('.')[0]: temp_config_dict})
                            break
            self.logger.debug('Config from environment variables - ' + str(config))
            return config
        
        except Exception as e:
            self.logger.error('Error loading environment variables: ' + str(traceback.print_tb(e.__traceback__)))
            
    def get_combined_config(self) -> dict:

        from mergedeep import merge
        try:
            # Build a config file using config.json if it exists    
            config_file = self.__load_config_file()

            # Override config.json if exists, with Environment variables for CI purposes
            config_env = self.__load_config_env()

            # Return merged config objects
            combined_config = merge(config_file, config_env)

            # Check if required fields exists in the config else return an exception. **Only works for strings in the config dictionary.**
            if "enabled" in combined_config["jira"].keys():

                if combined_config["jira"]["enabled"]:

                    from flatten_json import flatten
                    combined_config_key_list = flatten(combined_config, '.')

                    # Check for required fields. **Only works for strings in the config dictionary.**
                    is_field_not_found = 0
                    field_not_found_list = []
                    for field in self.required_fields:

                        if field not in combined_config_key_list:

                            is_field_not_found = 1
                            field_not_found_list.append(field)

                    if is_field_not_found:
                        self.logger.error('Missing config fields - ' + str(field_not_found_list))
                        raise

            return combined_config

        except Exception as e:
            self.logger.error('Error merging config: ' + str(traceback.print_tb(e.__traceback__)))
        