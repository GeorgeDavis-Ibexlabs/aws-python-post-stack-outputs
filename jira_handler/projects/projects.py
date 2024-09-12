import logging
from jira.client import JIRA

# Projects - class to manage JIRA Cloud projects
class Projects:

    # Projects Constructor
    # jira_credentials: JIRA credentials object 
    # logger: Logger object
    #
    # Returns: Projects object
    # Raises: None
    def __init__(self, jira_credentials: JIRA, logger: logging.Logger):
        self.jira = jira_credentials
        self.logger = logger

    # TODO: Create a new JIRA Cloud project
    def create_project(self):
        pass

    # Get all JIRA Cloud projects
    def get_projects(self) -> list:        
        projects = self.jira.projects()
        return projects

    # Check if project exists in JIRA Cloud
    def does_project_exist(self, project_key: str) -> tuple[bool, str]:

        projects = self.get_projects()

        self.logger.debug("List of ALL Projects - " + str(projects))    

        for project in projects:
            # key, name, id
            if project.key == project_key:
                return True, project.id

        return False
    
    def get_project_issue_types(self, project_id: str):

        issue_types_list =  self.jira.issue_types_for_project(
            projectIdOrKey = project_id
        )

        self.logger.debug("List of ALL Issue Types for Project ID " + project_id + " - " + str(issue_types_list))

        return issue_types_list

    def get_project_issue_type_by_name(self, project_id: str, issue_type_name: str):

        issue_types_list = self.get_project_issue_types(
            project_id = project_id
        )

        for issue_type in issue_types_list:

            if issue_type.raw["name"] == issue_type_name:
                return issue_type.raw["id"]

        