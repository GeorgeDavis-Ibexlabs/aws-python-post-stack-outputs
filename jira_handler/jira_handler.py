import logging
from jira import JIRA
from projects.projects import Projects
from issues.issues import Issues

class JiraHandler:

    # JiraHandler Constructor
    # logger: Logger object
    #
    # Returns: JiraHandler object
    # Raises: None
    def __init__(self, logger: logging.Logger, config: dict):
        
        self.logger = logger
        self.config = config

    # jira_create_issue: Creates an JIRA Object and creates a new issue on JIRA
    def jira_create_issue(self, issue_summary: str = '', issue_desc: str = ''):

        # Create a JIRA Object
        jira = JIRA(
            server=self.config["jira"]["cloud_url"],
            basic_auth=(self.config["jira"]["auth_email"],
            self.config["jira"]["api_token"])
        )

        # Create an Projects Object
        projectsObj = Projects(jira_credentials=jira, logger=self.logger)

        # Returns bool and project ID
        project_info = projectsObj.does_project_exist(self.config["jira"]["project_key"])

        if project_info[0]:

            # Create an Issues Object
            issueObj = Issues(
                logger=self.logger,
                jira_credentials=jira,
                project_key=self.config["jira"]["project_key"],
                project_id=project_info[1],
                email_domain="@" + str(self.config["jira"]["auth_email"].split('@')[1]),
                default_issue_labels=self.config["jira"]["default_issue_labels"],
            )
               
            # Building an JIRA issue
            self.logger.debug("JIRA Issue Summary: " + str(issue_summary))
            self.logger.debug("JIRA Issue Description: %s", issue_desc)

            # Update or Insert a JIRA issue. If the issue exists, then update it. If the issue doesn't exist, then create a new issue.
            issueObj.upsert_jira_issue(
                issue_summary = issue_summary,
                issue_desc = issue_desc,
                issue_type = "Task"
            )
                
            self.logger.info("Success.")

        else:
            raise Exception("JIRA Cloud Project does not exist.")