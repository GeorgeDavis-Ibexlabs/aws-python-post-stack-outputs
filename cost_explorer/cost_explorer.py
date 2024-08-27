import logging
import traceback
from boto3 import client

class CostExplorer:

    # CostExplorer Constructor
    # logger: Logger object
    #
    # Returns: CostExplorer object
    # Raises: None
    def __init__(self, logger: logging.Logger, costexplorer_client: client):
        
        self.logger = logger
        self.costexplorer_client = costexplorer_client

    # get_last_90_day_billing: Returns a `dict` of last 90 day AWS billing data 
    def __get_last_90_day_billing(self, group_by_parameters_list: list) -> dict:

        from datetime import datetime, timedelta

        # query_start_date = datetime.now() - timedelta(days=14) # Gets the date from 14 days ago. The start date is inclusive in the query.
        query_start_date = (datetime.now().replace(day=1) - timedelta(days=88)).replace(day=1) # Gets the first date of the previous month. End date is exclusive of the query period.
        query_end_date = datetime.now() # Gets the last date of the previous month. End date is exclusive.

        return self.costexplorer_client.get_cost_and_usage(
            TimePeriod={
                'Start': query_start_date.strftime('%Y-%m-%d'),
                'End': query_end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=[
                'UnblendedCost',
            ],
            GroupBy=group_by_parameters_list
        )

    # get_active_regions_from_last_90_day_billing: This method retrieves the active AWS regions from the last 90 days billing. Returns a `list` of active AWS regions.
    def get_active_regions_from_last_90_day_billing(self) -> list:

        try:
            group_by_parameters_list = [
                {
                    'Type': 'DIMENSION',
                    'Key': 'REGION'
                },
            ]
            billing_by_aws_region_response = self.__get_last_90_day_billing(group_by_parameters_list=group_by_parameters_list)

            self.logger.debug('Billing by AWS Region Response - ' + str(billing_by_aws_region_response))

            active_aws_regions = []
            excluded_billing_regions = ['global', 'NoRegion']

            for aws_region_results in billing_by_aws_region_response['ResultsByTime']:

                for aws_region_group in aws_region_results['Groups']:

                    if float(aws_region_group['Metrics']['UnblendedCost']['Amount']).__ceil__() > 0:

                        self.logger.debug('Region-wise spend in ' + aws_region_group['Keys'][0] + ' is $' + aws_region_group['Metrics']['UnblendedCost']['Amount'] + aws_region_group['Metrics']['UnblendedCost']['Unit'])

                        if aws_region_group['Keys'][0] not in active_aws_regions:

                            active_aws_regions.append(aws_region_group['Keys'][0])

            for excluded_region in excluded_billing_regions:

                if excluded_region in active_aws_regions:

                    self.logger.debug('Removed excluded billing region - ' + excluded_region + '.')
                    active_aws_regions.remove(excluded_region)

            return active_aws_regions
        
        except Exception as e:
            self.logger.error('CUR grouped by AWS Region Results Error - ' + str(traceback.print_tb(e.__traceback__)))
            return []

    # get_active_services_from_last_90_day_billing: This method retrieves the active AWS services from the last 90 days billing. Returns a `list` of active AWS services.
    def get_active_services_from_last_90_day_billing(self) -> list:
            
        try:
            group_by_parameters_list = [
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                },
            ]
            billing_by_aws_service_response = self.__get_last_90_day_billing(group_by_parameters_list=group_by_parameters_list)

            self.logger.debug('Billing by AWS Service Response - ' + str(billing_by_aws_service_response))

            active_aws_services = []

            for aws_service_results in billing_by_aws_service_response['ResultsByTime']:

                for aws_service_group in aws_service_results['Groups']:

                    if float(aws_service_group['Metrics']['UnblendedCost']['Amount']).__ceil__() > 0:

                        self.logger.debug('Service-wise spend in ' + aws_service_group['Keys'][0] + ' is $' + aws_service_group['Metrics']['UnblendedCost']['Amount'] + aws_service_group['Metrics']['UnblendedCost']['Unit'])

                        if aws_service_group['Keys'][0] not in active_aws_services:

                            active_aws_services.append(aws_service_group['Keys'][0])

            return active_aws_services

        except Exception as e:
            self.logger.error('CUR grouped by AWS Service Results Error - ' + str(traceback.print_tb(e.__traceback__)))
            return []

    # get_monthly_recurring_revenue_from_last_90_day_billing: Returns the last 90 day billing
    def get_monthly_recurring_revenue_from_last_90_day_billing(self) -> list:

        try:
            monthly_recurring_revenue_list = []
            monthly_recurring_revenue_billing_response = self.__get_last_90_day_billing(group_by_parameters_list=[])

            self.logger.debug('Last 90-day Billing Response - ' + str(monthly_recurring_revenue_billing_response))

            from datetime import datetime

            for monthly_bill in monthly_recurring_revenue_billing_response["ResultsByTime"]:

                if not monthly_bill["Estimated"]:

                    end_date = datetime.strptime(monthly_bill["TimePeriod"]["Start"], "%Y-%m-%d")
                    monthly_recurring_revenue_list.append(str(end_date.strftime('%B %Y')) + " - " + str(float(monthly_bill["Total"]["UnblendedCost"]["Amount"]).__round__(2)) + " " + monthly_bill["Total"]["UnblendedCost"]["Unit"])

                else:

                    end_date = datetime.strptime(monthly_bill["TimePeriod"]["Start"], "%Y-%m-%d")
                    monthly_recurring_revenue_list.append(str(end_date.strftime('%B %Y')) + " (Estimated) - " + str(float(monthly_bill["Total"]["UnblendedCost"]["Amount"]).__round__(2)) + " " + monthly_bill["Total"]["UnblendedCost"]["Unit"])

            return monthly_recurring_revenue_list

        except Exception as e:
            self.logger.error('CUR grouped monthly Results Error - ' + str(traceback.print_tb(e.__traceback__)))
            return []