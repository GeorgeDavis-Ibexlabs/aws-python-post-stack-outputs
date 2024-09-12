import logging

class Utils:

    # Utils Constructor
    # logger: Logger object
    #
    # Returns: Utils object
    # Raises: None
    def __init__(self, logger: logging.Logger):

        self.logger = logger
        self._region_map = { 'us-east-1': 'US East (N. Virginia)', 'us-east-2': 'US East (Ohio)', 'us-west-1': 'US West (N. California)', 'us-west-2': 'US West (Oregon)', 'af-south-1': 'Africa (Cape Town)', 'ap-east-1': 'Asia Pacific (Hong Kong)', 'ap-south-2': 'Asia Pacific (Hyderabad)', 'ap-southeast-3': 'Asia Pacific (Jakarta)', 'ap-southeast-5': 'Asia Pacific (Malaysia)', 'ap-southeast-4': 'Asia Pacific (Melbourne)', 'ap-south-1': 'Asia Pacific (Mumbai)', 'ap-northeast-3': 'Asia Pacific (Osaka)', 'ap-northeast-2': 'Asia Pacific (Seoul)', 'ap-southeast-1': 'Asia Pacific (Singapore)', 'ap-southeast-2': 'Asia Pacific (Sydney)', 'ap-northeast-1': 'Asia Pacific (Tokyo)', 'ca-central-1': 'Canada (Central)', 'ca-west-1': 'Canada West (Calgary)', 'cn-north-1': 'China (Beijing)', 'cn-northwest-1': 'China (Ningxia)', 'eu-central-1': 'Europe (Frankfurt)', 'eu-west-1': 'Europe (Ireland)', 'eu-west-2': 'Europe (London)', 'eu-south-1': 'Europe (Milan)', 'eu-west-3': 'Europe (Paris)', 'eu-south-2': 'Europe (Spain)', 'eu-north-1': 'Europe (Stockholm)', 'eu-central-2': 'Europe (Zurich)', 'il-central-1': 'Israel (Tel Aviv)', 'me-south-1': 'Middle East (Bahrain)', 'me-central-1': 'Middle East (UAE)', 'sa-east-1': 'South America (São Paulo)' }

    # get_region_name_by_id: Retrieve region name with region ID, returns `str`. 
    def get_region_name_by_id(self, region_id: str) -> str:
        return self._region_map[region_id]

    # convert_region_ids_to_region_names: Convert a list of region IDs to a list of region names, returns `list`. 
    def convert_region_ids_to_region_names(self, regions_list: list) -> list:

        region_names_list = []
        for region in regions_list:

            return region_names_list.append(self.get_region_name_by_id(region_id = region))