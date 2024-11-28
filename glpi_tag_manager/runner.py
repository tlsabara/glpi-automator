import logging
from sqlalchemy import create_engine, select, func, insert, Table, MetaData, and_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import time
import pandas as pd

load_dotenv()


class Runner:
    def __init__(self):
        """
        Initializes the class instance and sets up the configuration and database connection.

        Attributes:
            db_user (str): Database username from environment variable `DB_USER`.
            db_password (str): Database password from environment variable `DB_PASSWORD`.
            db_host (str): Database host from environment variable `DB_HOST`.
            db_database (str): Database name from environment variable `DB_DATABASE`.
            sleep_time (int): Time to sleep between loops, from environment variable `SLEEP_TIME` with a default of 10 seconds.
            database_uri (str): Database URI constructed from the database credentials and host.
            max_id (int): Maximum ID value set to 100.
            session (Session or None): SQLAlchemy session object, initialized as None.
            metadata (MetaData or None): SQLAlchemy metadata object, initialized as None.
            glpi_tickettasks (Table or None): SQLAlchemy Table object for GLPI ticket tasks, initialized as None.
            glpi_itilfollowups (Table or None): SQLAlchemy Table object for GLPI ITIL follow-ups, initialized as None.
            glpi_tickets_users (Table or None): SQLAlchemy Table object for GLPI tickets users, initialized as None.
            glpi_plugin_tag_tagitems (Table or None): SQLAlchemy Table object for GLPI plugin tag items, initialized as None.
            logger (Logger): Logger object for logging purposes.
            engine (Engine): SQLAlchemy engine instance created using the database URI.
            active_tasks (List or None): List of active tasks, initialized with `get_active_tasks` method.
            active_targets (List or None): List of active targets, initialized as None.

        Methods:
            validate_config(): Validates the configuration settings.
            create_session(): Creates a new SQLAlchemy session.
            get_active_tasks(): Retrieves a list of active tasks.
            load_max_id(): Loads the maximum ID value.
        """
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_database = os.getenv("DB_DATABASE")
        self.sleep_time = int(os.getenv("SLEEP_TIME", 10))
        self.database_uri = f'mysql+mysqlconnector://{self.db_user}:{self.db_password}@{self.db_host}:3306/{self.db_database}'
        self.max_id = 100
        self.session = None
        self.metadata = None
        self.glpi_tickettasks = None
        self.glpi_itilfollowups = None
        self.glpi_tickets_users = None
        self.glpi_plugin_tag_tagitems = None
        self.logger = logging.getLogger(__name__)

        self.validate_config()

        self.engine = create_engine(self.database_uri)
        self.create_session()

        self.active_tasks = self.get_active_tasks()
        self.active_targets = None

        self.create_session()
        self.load_max_id()

    def get_active_tasks(self):
        """
        :return: A pandas DataFrame containing active tasks with their IDs and associated ticket IDs.
        Tasks in state 2 are excluded.
        """
        self.logger.info('loading tasks...')

        ticket_tasks = self.session.execute(
            select(self.glpi_tickettasks.c.id, self.glpi_tickettasks.c.tickets_id).where(
                self.glpi_tickettasks.c.state != 2)
        )
        return pd.DataFrame(ticket_tasks.fetchall(), columns=ticket_tasks.keys())

        # return pd.read_sql("""
        # select
        #     id,
        #     tickets_id
        # from glpi_tickettasks
        # where state != 2
        # order by id desc
        # """, con=self.engine)

    def check_active_tasks(self):
        """
        Checks and updates the list of active tasks.

        :return: None
        """
        self.logger.info('checking active tasks...')
        self.active_targets = None
        actual_tasks = self.get_active_tasks()

        removed_tasks = self.active_tasks[~self.active_tasks['id'].isin(actual_tasks['id'])]
        if not removed_tasks.empty:
            self.active_targets = removed_tasks
        self.active_tasks = actual_tasks

    def link_return_tag(self):
        """
        Links a return tag to active tickets if the tag does not already exist.

        :return: None
        """
        self.logger.info('linking return tag...')

        if self.active_targets is not None and not self.active_targets.empty:
            self.active_targets = self.active_targets.astype(object).where(pd.notnull(self.active_targets), None)
            for _, row in self.active_targets.iterrows():
                ticket_id = int(row['tickets_id'])

                existing_link = self.session.execute(
                    select(self.glpi_plugin_tag_tagitems.c.id).where(
                        and_(
                            self.glpi_plugin_tag_tagitems.c.plugin_tag_tags_id == 8,
                            self.glpi_plugin_tag_tagitems.c.items_id == ticket_id,
                            self.glpi_plugin_tag_tagitems.c.itemtype == 'Ticket'
                        )
                    )
                ).first()
                if not existing_link:
                    self.session.execute(
                        insert(self.glpi_plugin_tag_tagitems).values(
                            plugin_tag_tags_id=8,
                            items_id=ticket_id,
                            itemtype='Ticket'
                        )
                    )
                    self.session.commit()
                    self.logger.info(f"Tag adicionada ao ticket {ticket_id}")
                else:
                    self.logger.info(f"Vínculo já existente para o ticket {ticket_id}")

    def validate_config(self):
        """
        Validates the database configuration by checking if
        the necessary configuration parameters (db_user, db_password, db_host, db_database)
        are present. Raises an exception if any parameter is missing.

        :return: None
        :raises: Exception if configuration is missing any required parameter
        """
        self.logger.info('validating configuration...')
        if not self.db_user or not self.db_password or not self.db_host or not self.db_database:
            raise Exception('missing configuration')
        self.logger.info('configuration valid...')

    def job(self):
        """
        Handles the main job execution loop that performs routine checks and processes tasks.

        The loop runs indefinitely, logging the current state, checking active tasks, linking return tags,
        processing GLPI followups, and then pauses for a pre-defined sleep time.

        :return: None
        """
        while True:
            self.logger.info('running...')
            self.check_active_tasks()
            self.link_return_tag()
            self.process_glpi_followups()
            self.logger.info('sleeping...')
            time.sleep(self.sleep_time)

    def create_session(self):
        """
        Creates a new database session and initializes metadata for specific tables.

        :return: None
        """
        self.logger.info('creating session...')
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.metadata = MetaData()
        self.glpi_tickettasks = Table('glpi_tickettasks', self.metadata, autoload_with=self.engine)
        self.glpi_itilfollowups = Table('glpi_itilfollowups', self.metadata, autoload_with=self.engine)
        self.glpi_tickets_users = Table('glpi_tickets_users', self.metadata, autoload_with=self.engine)
        self.glpi_plugin_tag_tagitems = Table('glpi_plugin_tag_tagitems', self.metadata, autoload_with=self.engine)
        self.logger.info('session created...')

    def load_max_id(self):
        """
        Loads the maximum ID from the `glpi_itilfollowups` table and sets it to the `max_id` attribute.

        :return: None
        """
        self.logger.info('loading max id...')
        self.max_id = self.session.query(func.ifnull(func.max(self.glpi_itilfollowups.c.id), 0)).scalar()

    def process_glpi_followups(self):
        """
        Processes follow-ups from the GLPI ITILFollowups table.

        This method fetches follow-ups from the database, filters by those which have an id greater than `max_id`, and processes them. For each follow-up, if the item type is "Ticket" and meets specific user and type criteria, it adds a tag to the ticket. It commits changes to the database and logs the actions performed or any errors encountered.

        :return: None
        """
        self.logger.info('processing glpi followups...')
        try:

            followups = self.session.execute(
                select(
                    self.glpi_itilfollowups.c.id,
                    self.glpi_itilfollowups.c.itemtype,
                    self.glpi_itilfollowups.c.items_id,
                    self.glpi_itilfollowups.c.users_id
                ).where(self.glpi_itilfollowups.c.id > self.max_id).order_by(self.glpi_itilfollowups.c.id)
            ).fetchall()

            for followup in followups:
                self.max_id, new_itemtype, new_items_id, new_users_id = followup

                if new_itemtype == 'Ticket':
                    result = self.session.execute(
                        select(
                            self.glpi_tickets_users.c.tickets_id
                        ).where(
                            and_(
                                self.glpi_tickets_users.c.tickets_id == new_items_id,
                                self.glpi_tickets_users.c.type == 1,
                                self.glpi_tickets_users.c.users_id == new_users_id
                            )
                        )
                    ).first()

                    if result:
                        self.session.execute(
                            insert(self.glpi_plugin_tag_tagitems).values(
                                plugin_tag_tags_id=9,
                                items_id=new_items_id,
                                itemtype='Ticket'
                            )
                        )
                        self.session.commit()
                        self.logger.info(f"Tag adicionada ao ticket {new_items_id} pelo usuário {new_users_id}")
                    else:
                        self.logger.info(f"O followup de ID {new_users_id} do ticket {new_items_id} não atende os requisitos!")
                else:
                    self.logger.info(f"Tipo de item {new_itemtype} desconhecido")

        except Exception as e:
            self.logger.info(f"Erro: {e}")
            self.session.rollback()

        finally:
            self.logger.info(f"Max ID: {self.max_id}")
            self.session.close()
            self.logger.info("Sessão encerrada")


if __name__ == "__main__":
    global_logger = logging.getLogger()
    global_logger.info("Starting core...")
    runner = Runner()
    runner.job()
