'''
Created on Oct 1, 2014

@author: fabiomignini
@author: giacomoratta

'''

import configparser, os, inspect, json
import logging
from do_core.exception import WrongConfigurationFile


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Configuration(object, metaclass=Singleton):

    def __init__(self):
        if os.getenv("FROG4_SDN_DO_CONF") is not None:
            self.conf_file = os.environ["FROG4_SDN_DO_CONF"]
        else:
            self.conf_file = "config/default-config.ini"
        self.log_init = False
        self.initialize()

    def initialize(self):

        config = configparser.RawConfigParser()
        base_folder = os.path.realpath(
            os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
        ).rpartition('/')[0]

        try:
            config.read(str(base_folder)+'/'+self.conf_file)

            # [domain_orchestrator]
            self.__ORCHESTRATOR_PORT = config.get('domain_orchestrator', 'port')
            self.__ORCHESTRATOR_IP = config.get('domain_orchestrator', 'ip')
            self.__DETACHED_MODE = config.getboolean('domain_orchestrator', 'detached_mode')

            # [log]
            self.__LOG_FILE = config.get('log', 'file')
            self.__LOG_LEVEL = config.get('log', 'log_level')
            self.__APPEND_LOG = config.getboolean('log', 'append_log')

            # [vlan]
            self.__VLAN_AVAILABLE_IDS = config.get('vlan', 'available_ids')
            self.__ALLOWED_VLANS = self.__set_available_vlan_ids_array(self.__VLAN_AVAILABLE_IDS)

            # [physical_ports]
            ports_json = config.get('physical_ports', 'ports')
            self.__PORTS = json.loads(ports_json)
            self.__GRE_BRIDGE = config.get('physical_ports', 'gre_bridge')
            self.__GRE_BRIDGE_ID = config.get('physical_ports', 'gre_bridge_id')

            # [authentication]
            self.__AUTH_TOKEN_EXPIRATION = config.get('authentication', 'token_expiration')

            # [database]
            self.__DATABASE_CONNECTION = config.get('database', 'connection')
            db_file = os.path.basename(self.__DATABASE_CONNECTION)
            self.__DATABASE_CONNECTION = self.__DATABASE_CONNECTION.replace(db_file, str(base_folder)+'/'+db_file)
            self.__DATABASE_DUMP_FILE = str(base_folder)+'/'+config.get('database', 'database_name')

            # [network_controller]
            self.__CONTROLLER_NAME = config.get('network_controller', 'controller_name')

            # [opendaylight]
            self.__ODL_USERNAME = config.get('opendaylight', 'odl_username')
            self.__ODL_PASSWORD = config.get('opendaylight', 'odl_password')
            self.__ODL_ENDPOINT = config.get('opendaylight', 'odl_endpoint')
            self.__ODL_VERSION = config.get('opendaylight', 'odl_version')

            # [onos]
            self.__ONOS_USERNAME = config.get('onos', 'onos_username')
            self.__ONOS_PASSWORD = config.get('onos', 'onos_password')
            self.__ONOS_ENDPOINT = config.get('onos', 'onos_endpoint')
            self.__ONOS_VERSION = config.get('onos', 'onos_version')

            # [ovsdb]
            self.__OVSDB_SUPPORT = config.getboolean('ovsdb', 'ovsdb_support')
            self.__OVSDB_NODE_IP = config.get('ovsdb', 'ovsdb_node_ip')
            self.__OVSDB_NODE_PORT = config.get('ovsdb', 'ovsdb_node_port')
            self.__OVSDB_IP = config.get('ovsdb', 'ovsdb_ip')

            # [nf_configuration]
            self.__INITIAL_CONFIGURATION = config.getboolean('nf_configuration', 'initial_configuration')
            self.__CONFIG_SERVICE_ENDPOINT = config.get('nf_configuration', 'config_service_endpoint')

            # [messaging]
            self.__DD_ACTIVATE = config.getboolean('messaging', 'dd_activate')
            self.__DD_NAME = config.get('messaging', 'dd_name')
            self.__DD_BROKER_ADDRESS = config.get('messaging', 'dd_broker_address')
            self.__DD_TENANT_NAME = config.get('messaging', 'dd_tenant_name')
            self.__DD_TENANT_KEY = config.get('messaging', 'dd_tenant_key')

            # [domain_description]
            self.__DOMAIN_DESCRIPTION_TOPIC = config.get('domain_description', 'domain_description_topic')
            self.__DOMAIN_DESCRIPTION_FILE = str(base_folder)+"/"+config.get('domain_description',
                                                                             'domain_description_file')
            self.__DOMAIN_DESCRIPTION_DYNAMIC_FILE = str(base_folder)+'/'+config.get('domain_description',
                                                                                     'domain_description_dynamic_file')
            self.__CAPABILITIES_APP_NAME = config.get('domain_description', 'capabilities_app_name')
            self.__DISCOVER_CAPABILITIES = config.getboolean('domain_description', 'discover_capabilities')

            # [other_options]
            self.__OO_CONSOLE_PRINT = config.getboolean('other_options', 'console_print')
            self.__USE_INTERFACES_NAMES = config.getboolean('other_options', 'use_interfaces_names')
            self.__JOLNET = config.getboolean('other_options', 'jolnet')

        except Exception as ex:
            raise WrongConfigurationFile(str(ex))

    def log_configuration(self):
        if not self.log_init and not self.__APPEND_LOG:
            try:
                os.remove(self.LOG_FILE)
            except OSError:
                pass
        log_format = '%(asctime)s.%(msecs)03d %(levelname)s %(message)s - %(filename)s:%(lineno)s'
        if self.__LOG_LEVEL == "DEBUG":
            log_level = logging.DEBUG
            requests_log = logging.getLogger("requests")
            requests_log.setLevel(logging.WARNING)
            sqlalchemy_log = logging.getLogger('sqlalchemy.engine')
            sqlalchemy_log.setLevel(logging.WARNING)
        elif self.__LOG_LEVEL == "INFO":
            log_level = logging.INFO
            requests_log = logging.getLogger("requests")
            requests_log.setLevel(logging.WARNING)
        elif self.__LOG_LEVEL == "WARNING":
            log_level = logging.WARNING
        else:
            log_level = logging.ERROR
        logging.basicConfig(filename=self.LOG_FILE, level=log_level, format=log_format, datefmt='%d/%m/%Y %H:%M:%S')
        logging.info("[CONFIG] Logging just started!")
        self.log_init = True

    def __set_available_vlan_ids_array(self, vid_ranges):

        """
        Expected vid_ranges = "280-289,62,737,90-95,290-299,13-56,92,57-82,2-5,12"
        """

        def __getKey(item):
            return item[0]

        vid_array = []
        if isinstance(vid_ranges, str):
            ranges = vid_ranges.split(",")
        else:
            ranges = vid_ranges

        for r in ranges:
            r = str(r)
            exs = r.split("-")
            if len(exs) == 1:
                exs.append(exs[0])
            elif len(exs) != 2:
                continue

            min_vlan_id = int(exs[0])
            max_vlan_id = int(exs[1])
            if (min_vlan_id > max_vlan_id):
                continue

            vid_array.append([min_vlan_id, max_vlan_id])
            #logging.debug("[CONFIG] - Available VLAN ID - Range: '" + r + "'")

        if len(vid_array) == 0:
            #logging.error("[CONFIG] - VLAN ID - No available vlan id read from '" + vid_ranges + "'")
            return []
        else:
            return sorted(vid_array, key=__getKey)

    @property
    def ORCHESTRATOR_PORT(self):
        return self.__ORCHESTRATOR_PORT

    @property
    def ORCHESTRATOR_IP(self):
        return self.__ORCHESTRATOR_IP

    @property
    def DETACHED_MODE(self):
        return self.__DETACHED_MODE

    @property
    def VLAN_AVAILABLE_IDS(self):
        return self.__VLAN_AVAILABLE_IDS

    @property
    def ALLOWED_VLANS(self):
        return self.__ALLOWED_VLANS

    @property
    def PORTS(self):
        return self.__PORTS

    @property
    def GRE_BRIDGE(self):
        return self.__GRE_BRIDGE

    @property
    def GRE_BRIDGE_ID(self):
        return self.__GRE_BRIDGE_ID

    @property
    def AUTH_TOKEN_EXPIRATION(self):
        return self.__AUTH_TOKEN_EXPIRATION

    @property
    def LOG_FILE(self):
        return self.__LOG_FILE

    @property
    def DATABASE_CONNECTION(self):
        return self.__DATABASE_CONNECTION

    @property
    def DATABASE_DUMP_FILE(self):
        return self.__DATABASE_DUMP_FILE

    @property
    def CONTROLLER_NAME(self):
        return self.__CONTROLLER_NAME

    @property
    def ODL_USERNAME(self):
        return self.__ODL_USERNAME

    @property
    def ODL_PASSWORD(self):
        return self.__ODL_PASSWORD

    @property
    def ODL_ENDPOINT(self):
        return self.__ODL_ENDPOINT

    @property
    def ODL_VERSION(self):
        return self.__ODL_VERSION

    @property
    def ONOS_USERNAME(self):
        return self.__ONOS_USERNAME

    @property
    def ONOS_PASSWORD(self):
        return self.__ONOS_PASSWORD

    @property
    def ONOS_ENDPOINT(self):
        return self.__ONOS_ENDPOINT

    @property
    def ONOS_VERSION(self):
        return self.__ONOS_VERSION

    @property
    def OVSDB_SUPPORT(self):
        return self.__OVSDB_SUPPORT

    @property
    def OVSDB_NODE_IP(self):
        return self.__OVSDB_NODE_IP

    @property
    def OVSDB_NODE_PORT(self):
        return self.__OVSDB_NODE_PORT

    @property
    def OVSDB_IP(self):
        return self.__OVSDB_IP

    @property
    def DD_ACTIVATE(self):
        return self.__DD_ACTIVATE

    @property
    def DD_NAME(self):
        return self.__DD_NAME

    @property
    def DD_BROKER_ADDRESS(self):
        return self.__DD_BROKER_ADDRESS

    @property
    def DD_TENANT_NAME(self):
        return self.__DD_TENANT_NAME

    @property
    def DD_TENANT_KEY(self):
        return self.__DD_TENANT_KEY

    @property
    def INITIAL_CONFIGURATION(self):
        return self.__INITIAL_CONFIGURATION

    @property
    def CONFIG_SERVICE_ENDPOINT(self):
        return self.__CONFIG_SERVICE_ENDPOINT

    @property
    def DOMAIN_DESCRIPTION_TOPIC(self):
        return self.__DOMAIN_DESCRIPTION_TOPIC

    @property
    def DOMAIN_DESCRIPTION_FILE(self):
        return self.__DOMAIN_DESCRIPTION_FILE

    @property
    def DOMAIN_DESCRIPTION_DYNAMIC_FILE(self):
        return self.__DOMAIN_DESCRIPTION_DYNAMIC_FILE

    @property
    def CAPABILITIES_APP_NAME(self):
        return self.__CAPABILITIES_APP_NAME

    @property
    def DISCOVER_CAPABILITIES(self):
        return self.__DISCOVER_CAPABILITIES

    @property
    def OO_CONSOLE_PRINT(self):
        return self.__OO_CONSOLE_PRINT

    @property
    def USE_INTERFACES_NAMES(self):
        return self.__USE_INTERFACES_NAMES

    @property
    def JOLNET(self):
        return self.__JOLNET
