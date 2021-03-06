"""
Created on Jun 20, 2015

@author: fabiomignini
@author: giacomoratta
@author: gabrielecastellano
"""

import datetime, logging, uuid

from do_core.config import Configuration
from domain_information_library.domain_info import DomainInfo
from nffg_library.nffg import NF_FG, EndPoint, FlowRule, Match, Action, VNF, Port

from sqlalchemy import Column, VARCHAR, Boolean, Integer, DateTime, Text, asc, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound
from do_core.sql.sql_server import get_session
from do_core.exception import GraphError

Base = declarative_base()


class GraphSessionModel(Base):
    __tablename__ = 'graph_session'
    attributes = ['session_id', 'user_id', 'graph_id', 'graph_name', 'status',
                  'started_at', 'last_update', 'error', 'ended', 'description']
    session_id = Column(VARCHAR(64), primary_key=True)
    user_id = Column(VARCHAR(64))
    graph_id = Column(Text)     # id in the json [see "forwarding-graph" section]
    graph_name = Column(Text)   # name in the json [see "forwarding-graph" section]
    status = Column(Text)       # = ( initialization | complete | updating | deleted | error )
    started_at = Column(DateTime)
    last_update = Column(DateTime, default=func.now())
    error = Column(DateTime)
    ended = Column(DateTime)
    description = Column(VARCHAR(256))


class PortModel(Base):
    __tablename__ = 'port'
    attributes = ['id', 'graph_port_id', 'status', 'switch_id', 'session_id'
                  'mac_address', 'ipv4_address', 'tunnel_remote_ip', 'vlan_id', 'gre_key', 'creation_date','last_update' ]
    id = Column(Integer, primary_key=True)
    graph_port_id = Column(VARCHAR(64)) # endpoint interface in the json [see "interface" section]
    status = Column(VARCHAR(64))        # = ( initialization | complete | error )
    switch_id = Column(VARCHAR(64))
    session_id = Column(VARCHAR(64))
    
    # port characteristics
    mac_address = Column(VARCHAR(64))
    ipv4_address = Column(VARCHAR(64))
    tunnel_remote_ip = Column(VARCHAR(64))
    vlan_id = Column(VARCHAR(64))
    gre_key = Column(VARCHAR(64))
    creation_date = Column(DateTime)
    last_update = Column(DateTime, default=func.now())
    

class EndpointModel(Base):
    __tablename__ = 'endpoint'
    attributes = ['id', 'graph_endpoint_id','name','type','session_id']
    id = Column(Integer, primary_key=True) 
    graph_endpoint_id = Column(VARCHAR(64)) # id in the json [see "end-points" section]
    name = Column(VARCHAR(64))  # name in the json [see "end-points" section]
    type = Column(VARCHAR(64))  # = ( internal | interface | interface-out | vlan | gre ) [see "end-points" section]
    session_id = Column(VARCHAR(64))

    
class EndpointResourceModel(Base):
    '''
        resource_type: flow-rule type must have the resource_id equal to the flow-rules
                       that connect the end-point to an external end-point.
    '''
    __tablename__ = 'endpoint_resource'
    attributes = ['endpoint_id', 'resource_type', 'resource_id']
    endpoint_id = Column(Integer, primary_key=True)
    resource_type = Column(VARCHAR(64), primary_key=True)  # = ( port | flow-rule )
    resource_id = Column(Integer, primary_key=True)
    

class FlowRuleModel(Base):
    __tablename__ = 'flow_rule'
    attributes = ['id', 'graph_flow_rule_id', 'internal_id', 'session_id', 
                  'switch_id', 'type', 'priority','status', 'creation_date','last_update','description']
    id = Column(Integer, primary_key=True)
    graph_flow_rule_id = Column(VARCHAR(64)) # id in the json [see "flow-rules" section]
    internal_id = Column(VARCHAR(64)) # auto-generated id, for the same graph_flow_rule_id
    session_id = Column(VARCHAR(64))
    
    switch_id = Column(VARCHAR(64))
    type = Column(VARCHAR(64))      # = ( NULL | external ) [NULL indicates an internal flowrule written in nffg.json]
    priority = Column(VARCHAR(64))  # priority in the json [see "flow-rules" section] 
    status = Column(VARCHAR(64))    # = ( initialization | complete | error )
    creation_date = Column(DateTime)
    last_update = Column(DateTime, default=func.now())
    description = Column(VARCHAR(128))
    

class MatchModel(Base):
    __tablename__ = 'match'
    attributes = ['id', 'flow_rule_id', 'port_in_type', 'port_in', 'ether_type','vlan_id','vlan_priority', 'source_mac','dest_mac','source_ip',
                 'dest_ip','tos_bits','source_port', 'dest_port', 'protocol']
    id = Column(Integer, primary_key=True)
    flow_rule_id = Column(Integer)      # = FlowRuleModel.id
    port_in_type = Column(VARCHAR(64))  # = ( port | endpoint )
    
    # match characteristics
    port_in = Column(VARCHAR(64))
    ether_type = Column(VARCHAR(64))
    vlan_id = Column(VARCHAR(64))
    vlan_priority = Column(VARCHAR(64))
    source_mac = Column(VARCHAR(64))
    dest_mac = Column(VARCHAR(64))
    source_ip = Column(VARCHAR(64))
    dest_ip = Column(VARCHAR(64))
    tos_bits = Column(VARCHAR(64))
    source_port = Column(VARCHAR(64))
    dest_port = Column(VARCHAR(64))
    protocol = Column(VARCHAR(64))
    

class ActionModel(Base):
    __tablename__ = 'action'
    attributes = ['id', 'flow_rule_id', 'output_type', 'output_to_port', 'output_to_controller', '_drop', 
                  'set_vlan_id','set_vlan_priority', 'push_vlan', 'pop_vlan', 
                  'set_ethernet_src_address', 'set_ethernet_dst_address',
                  'set_ip_src_address','set_ip_dst_address', 'set_ip_tos',
                  'set_l4_src_port','set_l4_dst_port', 'output_to_queue']    
    id = Column(Integer, primary_key=True)
    flow_rule_id = Column(Integer)      # = FlowRuleModel.id
    output_type = Column(VARCHAR(64))   # = ( port | endpoint )
    
    # action characteristics
    output_to_port = Column(VARCHAR(64))        # e.g. output port, endpoint interface
    output_to_controller = Column(Boolean)        # if 'true' it sends packets to controller (e.g. CONTROLLER:65535) 
    _drop = Column(Boolean)
    set_vlan_id = Column(VARCHAR(64))
    set_vlan_priority = Column(VARCHAR(64))
    push_vlan = Column(VARCHAR(64))
    pop_vlan = Column(Boolean)
    set_ethernet_src_address = Column(VARCHAR(64))
    set_ethernet_dst_address = Column(VARCHAR(64))
    set_ip_src_address = Column(VARCHAR(64))
    set_ip_dst_address = Column(VARCHAR(64))
    set_ip_tos = Column(VARCHAR(64))
    set_l4_src_port = Column(VARCHAR(64))
    set_l4_dst_port = Column(VARCHAR(64))
    output_to_queue = Column(VARCHAR(64))


class VlanModel(Base):
    __tablename__ = 'vlan'
    attributes = ['id', 'flow_rule_id', 'switch_id', 'port_in', 'vlan_in', 'port_out', 'vlan_out']
    id = Column(Integer, primary_key=True)
    flow_rule_id = Column(Integer)
    switch_id = Column(VARCHAR(64))
    port_in = Column(Integer)
    vlan_in = Column(Integer)
    port_out = Column(Integer)
    vlan_out = Column(Integer)


class VnfModel(Base):
    __tablename__ = 'vnf'
    attributes = ['id', 'graph_vnf_id', 'session_id', 'name', 'template', 'application_name']
    id = Column(Integer, primary_key=True)
    graph_vnf_id = Column(VARCHAR(64))
    session_id = Column(VARCHAR(64))
    name = Column(VARCHAR(64))
    template = Column(VARCHAR(64))
    application_name = Column(VARCHAR(64))


class VnfPortModel(Base):
    __tablename__ = 'vnf_port'
    attributes = ['id', 'graph_port_id', 'vnf_id', 'name']
    id = Column(Integer, primary_key=True)
    graph_port_id = Column(VARCHAR(64))
    vnf_id = Column(Integer)
    name = Column(VARCHAR(64))


# ------------------------------------------


class GraphSession(object):
    def __init__(self):
        pass
    
    
    '''
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        DATABASE INTERFACE - GET section "def get*" and other releated functions
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    '''
    
    def getActiveUserGraphSession(self, user_id, graph_id, error_aware=True):
        session = get_session()
        if error_aware:
            session_ref = session.query(GraphSessionModel).filter_by(user_id = user_id).filter_by(graph_id = graph_id).filter_by(ended = None).filter_by(error = None).first()
        else:
            session_ref = session.query(GraphSessionModel).filter_by(user_id = user_id).filter_by(graph_id = graph_id).filter_by(ended = None).order_by(desc(GraphSessionModel.started_at)).first()  
        return session_ref
    
    
    def getAllExternalFlowrules(self):
        session = get_session()
        return session.query(FlowRuleModel).filter_by(type = 'external').all()

    def getEndpointByID(self, endpoint_id):
        session = get_session()
        try:
            ep = session.query(EndpointModel).filter_by(id = endpoint_id).one()
            return ep
        except:
            return None
    
    def getEndpointByGraphID(self, graph_endpoint_id, session_id):
        session = get_session()
        try:
            ep = session.query(EndpointModel).filter_by(session_id = session_id).filter_by(graph_endpoint_id = graph_endpoint_id).one()
            return ep
        except:
            return None
    
    
    def getEndpointsBySessionID(self, session_id):
        session = get_session()
        try:
            ep = session.query(EndpointModel).filter_by(session_id = session_id).all()
            return ep
        except:
            return None

    def getVnfsBySessionID(self, session_id):
        session = get_session()
        try:
            ep = session.query(VnfModel).filter_by(session_id=session_id).all()
            return ep
        except:
            return None
    
    def getEndpointResourcesByEndpointID(self, endpoint_id):
        session = get_session()
        try:
            eprs = session.query(EndpointResourceModel).filter_by(endpoint_id = endpoint_id).all()
            return eprs
        except:
            return None

    def getEndpointResourcesPortByEndpointID(self, endpoint_id):
        session = get_session()
        try:
            eprs = session.query(EndpointResourceModel)\
                .filter_by(endpoint_id=endpoint_id)\
                .filter_by(resource_type='port')\
                .one()
            return eprs
        except:
            return None

    def getFlowruleByID(self, flow_rule_id=None):
        try:
            session = get_session()
            return session.query(FlowRuleModel).filter_by(id=flow_rule_id).one()
        except:
            return None
    
    def getFlowruleByInternalID(self, internal_id=None):
        try:
            session = get_session()
            return session.query(FlowRuleModel).filter_by(internal_id=internal_id).one()
        except:
            return None
        return None
        
    
    def getFlowrules(self, session_id, graph_flow_rule_id=None):
        session = get_session()
        if graph_flow_rule_id is None:
            return session.query(FlowRuleModel).filter_by(session_id = session_id).all()
        else:
            return session.query(FlowRuleModel).filter_by(session_id = session_id).filter_by(graph_flow_rule_id = graph_flow_rule_id).all()


    def getVnfByID(self, session_id, vnf_id):
        try:
            session = get_session()
            return session.query(VnfModel).filter_by(session_id=session_id, graph_vnf_id=vnf_id).one()
        except:
            return None

    def getVnfPortsByVnfID(self, vnf_id):
        try:
            session = get_session()
            return session.query(VnfPortModel).filter_by(vnf_id=vnf_id).all()
        except:
            return None

    def getNewUnivocalSessionID(self):
        '''
        Compute a new session id 32 byte long.
        Check if it is already exists: if yes, repeat the computation. 
        '''
        session = get_session()
        rows = session.query(GraphSessionModel.session_id).all()
        
        while True:
            session_id = uuid.uuid4().hex
            found = False
            for row in rows:
                if(row.session_id == session_id):
                    found = True
                    break
            if found==False:
                return session_id
    
    
    def getFlowruleProgressionPercentage(self,session_id,nffg_id):
        session = get_session()
        percentage = 0
        
        flowrules = session.query(FlowRuleModel).filter_by(session_id=session_id).all()
        count_flowrules = len(flowrules)
        if count_flowrules<=0:
            return 0
        
        for fr in flowrules:
            internal_flowrules = session.query(FlowRuleModel).filter_by(session_id=session_id).filter_by(graph_flow_rule_id=fr.graph_flow_rule_id).filter_by(type='external').all()
            if len(internal_flowrules)>0:
                percentage = percentage+1
        
        return ( percentage / count_flowrules * 100 )
    
    
    def getMatchByFlowruleID(self, flowrule_id):
        try:
            session = get_session()
            return session.query(MatchModel).filter_by(flow_rule_id=flowrule_id).one()
        except:
            return None
        return None
        
    
    def getEndpointVlanInIDs(self, port_in, switch_id):
        session = get_session()
        qref = session.query(FlowRuleModel,MatchModel).\
            filter(FlowRuleModel.id == MatchModel.flow_rule_id).\
            filter(FlowRuleModel.switch_id == switch_id).\
            filter(MatchModel.port_in == port_in).\
            all()
        if len(qref)>0:
            return qref
        return None
        
        
     
        
    def getVlanInIDs(self, port_in, switch_id):
        session = get_session()
        return session.query(VlanModel).filter_by(switch_id=switch_id).filter_by(port_in=port_in).order_by(asc(VlanModel.vlan_in)).all()
    
    
    def isDirectEndpoint(self, port_in, switch_id):
        session = get_session()
        if port_in is None or switch_id is None:
            return False
        query_ref = session.query(VlanModel.id).filter_by(vlan_in=None).filter_by(switch_id=switch_id).filter_by(port_in=port_in).all()
        if len(query_ref)>0:
            return True
        return False
    
    
    def ingressVlanIsBusy(self, vlan_in, port_in, switch_id, query_ref=None):
        session = get_session()
        if vlan_in is None or port_in is None or switch_id is None:
            return False
        new_query_ref = session.query(VlanModel).filter_by(vlan_in=vlan_in).filter_by(switch_id=switch_id).filter_by(port_in=port_in).all()
        if len(new_query_ref)>0:
            if query_ref is not None:
                query_ref.clear()
                query_ref.extend(new_query_ref)
            return True
        return False
    
    
    def externalFlowruleExists(self, switch_id, internal_id):
        session = get_session()
        try:
            session.query(FlowRuleModel).filter_by(internal_id=internal_id).filter_by(switch_id=switch_id).filter_by(type='external').one()
            return True
        except:
            return False
    
    
    def getExternalFlowrulesByGraphFlowruleID(self, switch_id, graph_flow_rule_id):
        #return all flowrules with a graph_flow_rule_id, ordered by "internal_id" (asc) 
        session = get_session()
        flow_rules_ref = session.query(FlowRuleModel).filter_by(graph_flow_rule_id=graph_flow_rule_id).filter_by(switch_id=switch_id).filter_by(type='external').order_by(asc(FlowRuleModel.internal_id)).all()
        return flow_rules_ref

    def getFlowruleOnTheSwitch(self, switch_id, port_in, nffg_fr):
        session = get_session()
        qref = session.query(FlowRuleModel, MatchModel).\
            filter(FlowRuleModel.id == MatchModel.flow_rule_id).\
            filter(FlowRuleModel.priority == nffg_fr.priority).\
            filter(FlowRuleModel.switch_id == switch_id).\
            filter(MatchModel.port_in == port_in).\
            filter(MatchModel.vlan_id == nffg_fr.match.vlan_id).\
            filter(MatchModel.vlan_priority == nffg_fr.match.vlan_priority).\
            filter(MatchModel.ether_type == nffg_fr.match.ether_type).\
            filter(MatchModel.source_mac == nffg_fr.match.source_mac).\
            filter(MatchModel.dest_mac == nffg_fr.match.dest_mac).\
            filter(MatchModel.source_ip == nffg_fr.match.source_ip).\
            filter(MatchModel.dest_ip == nffg_fr.match.dest_ip).\
            filter(MatchModel.tos_bits == nffg_fr.match.tos_bits).\
            filter(MatchModel.source_port == nffg_fr.match.source_port).\
            filter(MatchModel.dest_port == nffg_fr.match.dest_port).\
            filter(MatchModel.protocol == nffg_fr.match.protocol).\
            all()
        if len(qref)>0:
            return qref
        return None

    def getFlowruleMatchesOnTheSwitch(self, switch_id, port_in, nffg_match):
        session = get_session()
        qref = session.query(FlowRuleModel, MatchModel).\
            filter(FlowRuleModel.id == MatchModel.flow_rule_id).\
            filter(FlowRuleModel.switch_id == switch_id).\
            filter(MatchModel.port_in == port_in).\
            filter(MatchModel.ether_type == nffg_match.ether_type).\
            filter(MatchModel.source_mac == nffg_match.source_mac).\
            filter(MatchModel.dest_mac == nffg_match.dest_mac).\
            filter(MatchModel.source_ip == nffg_match.source_ip).\
            filter(MatchModel.dest_ip == nffg_match.dest_ip).\
            filter(MatchModel.tos_bits == nffg_match.tos_bits).\
            filter(MatchModel.source_port == nffg_match.source_port).\
            filter(MatchModel.dest_port == nffg_match.dest_port).\
            filter(MatchModel.protocol == nffg_match.protocol).\
            all()
        if len(qref)>0:
            return qref
        return None

    def getBusyVlanInOnTheSwitch(self, switch_id, port_in, nffg_match):
        qref = self.getFlowruleMatchesOnTheSwitch(switch_id, port_in, nffg_match)
        
        # Collect the ingress VLAN IDs
        busy_vlan_ids = []
        if qref is not None:
            for fr in qref:
                if fr.MatchModel.vlan_id is not None:
                    busy_vlan_ids.append(int(fr.MatchModel.vlan_id))
        return busy_vlan_ids

    def getPortById(self, port_id):
        session = get_session()
        return session.query(PortModel).filter_by(id=port_id).one()

    def getPort(self, graph_endpoint_id):
        session = get_session()
        endpoint = session.query(EndpointModel).filter_by(graph_endpoint_id=graph_endpoint_id).one()
        endpoint_resource = session.query(EndpointResourceModel)\
            .filter_by(endpoint_id=endpoint.id)\
            .filter_by(resource_type='port').one()

        return session.query(PortModel).filter_by(id=endpoint_resource.resource_id).one()

    def getNextGreInterfaceName(self):
        session = get_session()
        ports = session.query(PortModel).order_by(asc(PortModel.graph_port_id)).all()
        last_gre_interface_name = "gre-1"
        for port in ports:
            if 'gre' in port.graph_port_id:
                last_gre_interface_name = port.graph_port_id
        return 'gre' + str(int(last_gre_interface_name.replace('gre', '')) + 1)

    
    '''
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        DATABASE INTERFACE - INSERT section "def add*"
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    '''
    
    def addFlowrule(self, session_id, switch_id, flow_rule, nffg=None):   

        # build flowrule type
        if flow_rule.type != 'external':
            flowrule_type = None
            if flow_rule.match is not None:
                if flow_rule.match.port_in.split(':')[0] == 'endpoint':
                    flowrule_type = 'ep'
                elif flow_rule.match.port_in.split(':')[0] == 'vnf':
                    flowrule_type = 'vnf'
            if len(flow_rule.actions) > 0:
                for action in flow_rule.actions:
                    if action.output is not None:
                        flowrule_type += '-to-'
                        if action.output.split(':')[0] == 'endpoint':
                            flowrule_type += 'ep'
                        elif action.output.split(':')[0] == 'vnf':
                            flowrule_type += 'vnf'
            flow_rule.type = flowrule_type

        # FlowRule
        flow_rule_db_id = self.dbStoreFlowrule(session_id, flow_rule, None, switch_id)
        
        # Match
        if nffg is not None and flow_rule.match is not None:
            match_db_id = flow_rule_db_id
            port_in_type = None
            port_in = None
            if flow_rule.match.port_in.split(':')[0] == 'endpoint':
                port_in_type = 'endpoint'
                port_in = nffg.getEndPoint(flow_rule.match.port_in.split(':', 1)[1]).db_id
                self.dbStoreEndpointResourceFlowrule(port_in, flow_rule_db_id)
            if flow_rule.match.port_in.split(':')[0] == 'vnf':
                port_in_type = 'vnf'
                vnf_id = flow_rule.match.port_in.split(':')[1]
                port_id = flow_rule.match.port_in.split(':', 2)[2]
                port_in = nffg.getVNF(vnf_id).getPort(port_id).db_id
            self.dbStoreMatch(flow_rule.match, flow_rule_db_id, match_db_id, port_in=port_in, port_in_type=port_in_type)
        
        # Actions
        if nffg is not None and len(flow_rule.actions)>0:
            for action in flow_rule.actions:
                output_type = None
                output_port = None
                if action.output is not None and action.output.split(':')[0] == 'endpoint':
                    output_type = 'endpoint'
                    output_port = nffg.getEndPoint(action.output.split(':', 1)[1]).db_id
                    self.dbStoreEndpointResourceFlowrule(output_port, flow_rule_db_id)
                if action.output is not None and action.output.split(':')[0] == 'vnf':
                    output_type = 'vnf'
                    vnf_id = action.output.split(':')[1]
                    port_id = action.output.split(':', 2)[2]
                    output_port = nffg.getVNF(vnf_id).getPort(port_id).db_id
                self.dbStoreAction(action, flow_rule_db_id, None, output_to_port=output_port, output_type=output_type)

        return flow_rule_db_id

    def addPort(self, session_id, endpoint_id, port_id, graph_port_id, switch_id, vlan_id, status, local_ip, remote_ip, gre_key):
        port_id = self.dbStorePort(session_id, port_id, graph_port_id, switch_id, vlan_id, status, local_ip, remote_ip, gre_key)
        self.dbStoreEndpointResourcePort(endpoint_id, port_id)

    def addVlanTracking(self, flow_rule_id, switch_id, vlan_in, port_in, vlan_out, port_out):
        session = get_session()
        
        max_id = session.query(func.max(VlanModel.id).label("max_id")).one().max_id
        if max_id  is None:
            max_id = 0
        else:
            max_id = int(max_id)+1
        
        with session.begin():    
            vlan_ref = VlanModel(id=max_id, flow_rule_id=flow_rule_id, switch_id=switch_id, vlan_in=vlan_in, port_in=port_in, vlan_out=vlan_out, port_out=port_out)
            session.add(vlan_ref) 

    def addVnf(self, session_id, switch_id, vnf, nffg=None, application_name=None):

        # NFV
        nfv_db_id = self.dbStoreVnf(session_id, vnf, None, switch_id, application_name)

        # Ports
        if nffg is not None and len(vnf.ports) > 0:
            for port in vnf.ports:
                self.dbStoreVnfPort(None, port.id, nfv_db_id, port.name)

        return nfv_db_id

    '''
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        DATABASE INTERFACE - UPDATE section "def update*"
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    '''
    
    def updateEnded(self, session_id):
        session = get_session() 
        with session.begin():       
            session.query(GraphSessionModel).filter_by(session_id=session_id).update({"ended":datetime.datetime.now(),"status":"deleted"}, synchronize_session = False)


    def updateError(self, session_id):
        session = get_session()
        with session.begin():
            session.query(GraphSessionModel).filter_by(session_id=session_id).update({"error":datetime.datetime.now(),"status":"error"}, synchronize_session = False)


    def updateStatus(self, session_id, status, error=False):
        session = get_session()
        with session.begin():
            session.query(GraphSessionModel).filter_by(session_id=session_id).update({"last_update":datetime.datetime.now(), 'status':status})


    '''
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        DATABASE INTERFACE - DELETE section "def delete*"
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    '''
    
    def cleanAll(self):
        session = get_session()
        session.query(ActionModel).delete()
        session.query(EndpointModel).delete()
        session.query(EndpointResourceModel).delete()
        session.query(FlowRuleModel).delete()
        session.query(GraphSessionModel).delete()
        session.query(MatchModel).delete()
        session.query(PortModel).delete()
        session.query(VlanModel).delete()
        session.query(GraphSessionModel).delete()
        session.query(VnfModel).delete()
        session.query(VnfPortModel).delete()
    
    
    def deleteEndpointByID(self, endpoint_id):
        # delete from tables: EndpointModel.
        session = get_session()
        with session.begin():
            session.query(EndpointModel).filter_by(id = endpoint_id).delete()


    def deleteEndpointByGraphID(self, graph_endpoint_id, session_id):
        # delete from tables: EndpointModel.
        session = get_session()
        with session.begin():
            session.query(EndpointModel).filter_by(session_id = session_id).filter_by(graph_endpoint_id = graph_endpoint_id).delete()
    

    def deleteFlowruleByID(self, flow_rule_id):
        # delete from tables: FlowRuleModel, MatchModel, ActionModel, VlanModel, EndpointResourceModel.
        session = get_session()
        with session.begin():
            session.query(FlowRuleModel).filter_by(id=flow_rule_id).delete()
            session.query(MatchModel).filter_by(flow_rule_id=flow_rule_id).delete()
            session.query(ActionModel).filter_by(flow_rule_id=flow_rule_id).delete()
            session.query(VlanModel).filter_by(flow_rule_id=flow_rule_id).delete()
            session.query(EndpointResourceModel).filter_by(resource_id=flow_rule_id).filter_by(resource_type='flow-rule').delete()
    
    
    def deletePort(self,  port_id, session_id):
        # delete from tables: PortModel, EndpointResourceModel.
        session = get_session()
        with session.begin():
            session.query(PortModel).filter_by(id = port_id).filter_by(session_id=session_id).delete()
            session.query(EndpointResourceModel).filter_by(resource_id=port_id).filter_by(resource_type='port').delete()

    def deleteVnfByID(self, vnf_id):
        session = get_session()
        with session.begin():
            session.query(VnfModel).filter_by(id=vnf_id).delete()

    def deleteVnfPortByID(self, vnf_port_id):
        session = get_session()
        with session.begin():
            session.query(VnfPortModel).filter_by(id=vnf_port_id).delete()



  
    '''
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        DB STORE FUNCTIONS "def dbStore*"
        These functions works only with the database to add new records.
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    '''
    
    def dbStoreAction(self, action, flow_rule_db_id, action_db_id=None, output_to_port=None, output_type=None):    
        session = get_session()
        
        if action_db_id is None:
            action_db_id = session.query(func.max(ActionModel.id).label("max_id")).one().max_id
            if action_db_id is None:
                action_db_id = 0
            else:
                action_db_id = int(action_db_id) + 1
        
        if output_to_port is None:
            output_to_port=action.output
            
        with session.begin():
            action_ref = ActionModel(id=action_db_id, flow_rule_id=flow_rule_db_id,
                                     output_type=output_type, output_to_port=output_to_port,
                                     output_to_controller=action.controller, _drop=action.drop, set_vlan_id=action.set_vlan_id,
                                     set_vlan_priority=action.set_vlan_priority, push_vlan=action.push_vlan, pop_vlan=action.pop_vlan,
                                     set_ethernet_src_address=action.set_ethernet_src_address, 
                                     set_ethernet_dst_address=action.set_ethernet_dst_address,
                                     set_ip_src_address=action.set_ip_src_address, set_ip_dst_address=action.set_ip_dst_address,
                                     set_ip_tos=action.set_ip_tos, set_l4_src_port=action.set_l4_src_port,
                                     set_l4_dst_port=action.set_l4_dst_port, output_to_queue=action.output_to_queue)
            session.add(action_ref)
            return action_ref

    def dbStoreVnf(self, session_id, vnf, vnf_db_id, switch_id, application_name):
        session = get_session()
        if vnf_db_id is None:
            vnf_db_id = session.query(func.max(VnfModel.id).label("max_id")).one().max_id
            if vnf_db_id is None:
                vnf_db_id = 0
            else:
                vnf_db_id = int(vnf_db_id) + 1
        with session.begin():
            vnf_ref = VnfModel(id=vnf_db_id, graph_vnf_id=vnf.id, session_id=session_id, name=vnf.name,
                               template=vnf.vnf_template_location, application_name=application_name)
            session.add(vnf_ref)
            return vnf_db_id

    def dbStoreVnfPort(self, vnf_port_id, graph_vnf_port_id, vnf_db_id, name):
        session = get_session()
        if vnf_port_id is None:
            vnf_port_id = session.query(func.max(VnfPortModel.id).label("max_id")).one().max_id
            if vnf_port_id is None:
                vnf_port_id = 0
            else:
                vnf_port_id = int(vnf_port_id) + 1
        with session.begin():
            vnf_port_ref = VnfPortModel(id=vnf_port_id, graph_port_id=graph_vnf_port_id,
                                        vnf_id=vnf_db_id, name=name)
            session.add(vnf_port_ref)
            return vnf_port_id

    def dbStoreEndpoint(self, session_id, endpoint_id, graph_endpoint_id, name, _type):
        session = get_session()
        if endpoint_id is None:
            endpoint_id = session.query(func.max(EndpointModel.id).label("max_id")).one().max_id
            if endpoint_id is None:
                endpoint_id = 0
            else:
                endpoint_id=int(endpoint_id)+1
        with session.begin():
            endpoint_ref = EndpointModel(id=endpoint_id, graph_endpoint_id=graph_endpoint_id, 
                                         session_id=session_id, name=name, type=_type)
            session.add(endpoint_ref)
            return endpoint_id

    def dbStoreEndpointResourcePort(self, endpoint_id, port_id):
        session = get_session()
        with session.begin():
            ep_res_ref = EndpointResourceModel(endpoint_id=endpoint_id, resource_type='port', resource_id=port_id)
            session.add(ep_res_ref)
    def dbStoreEndpointResourceFlowrule(self, endpoint_id, flow_rule_id):
        session = get_session()
        with session.begin():
            ep_res_ref = EndpointResourceModel(endpoint_id=endpoint_id,resource_type='flow-rule',resource_id=flow_rule_id)
            session.add(ep_res_ref)

    def dbStoreFlowrule(self, session_id, flow_rule, flow_rule_db_id, switch_id):
        session = get_session()
        if flow_rule_db_id is None:
            flow_rule_db_id = session.query(func.max(FlowRuleModel.id).label("max_id")).one().max_id
            if flow_rule_db_id is None:
                flow_rule_db_id = 0
            else:
                flow_rule_db_id=int(flow_rule_db_id)+1
        with session.begin():
            flow_rule_ref = FlowRuleModel(id=flow_rule_db_id, internal_id=flow_rule.internal_id, 
                                       graph_flow_rule_id=flow_rule.id, session_id=session_id, switch_id=switch_id,
                                       priority=flow_rule.priority,  status=None, description=flow_rule.description,
                                       creation_date=datetime.datetime.now(), last_update=datetime.datetime.now(), type=flow_rule.type)
            session.add(flow_rule_ref)
            return flow_rule_db_id

    def dbStoreGraphSessionFromNffgObject(self, session_id, user_id, nffg):
        session = get_session()
        with session.begin():
            graphsession_ref = GraphSessionModel(session_id=session_id, user_id=user_id, graph_id=nffg.id, 
                                started_at = datetime.datetime.now(), graph_name=nffg.name,
                                last_update = datetime.datetime.now(), status='inizialization',
                                                 description=nffg.description)
            session.add(graphsession_ref)

    def dbStoreMatch(self, match, flow_rule_db_id, match_db_id, port_in=None, port_in_type=None):
        session = get_session()
        with session.begin():
            
            if port_in is None:
                port_in=match.port_in
            
            # Flowrule and match have a 1:1 relationship,
            # so the match record can have the same id of the flowrule record!
            match_ref = MatchModel(id=match_db_id, flow_rule_id=flow_rule_db_id, 
                                   port_in_type=port_in_type, port_in=port_in,
                                   ether_type=match.ether_type, vlan_id=match.vlan_id,
                                   vlan_priority=match.vlan_priority, source_mac=match.source_mac,
                                   dest_mac=match.dest_mac, source_ip=match.source_ip,
                                   dest_ip=match.dest_ip, tos_bits=match.tos_bits,
                                   source_port=match.source_port, dest_port=match.dest_port,
                                   protocol=match.protocol)
            session.add(match_ref)
            return match_ref
    
    def dbStorePort(self, session_id, port_id, graph_port_id, switch_id, vlan_id, status, local_ip, remote_ip, gre_key):
        session = get_session()
        if port_id is None:
            port_id = session.query(func.max(PortModel.id).label("max_id")).one().max_id
            if port_id is None:
                port_id = 0
            else:
                port_id=int(port_id)+1
        with session.begin():
            port_ref = PortModel(id=port_id, 
                                 graph_port_id=graph_port_id,
                                 session_id=session_id, status=status, 
                                 switch_id=switch_id,
                                 vlan_id=vlan_id,
                                 ipv4_address=local_ip,
                                 tunnel_remote_ip=remote_ip,
                                 gre_key=gre_key,
                                 creation_date=datetime.datetime.now(), 
                                 last_update=datetime.datetime.now())
            session.add(port_ref)
            return port_id

    '''
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        MAIN FUNCTIONS
        These functions manage the main operations with a NFFG: add, update, get.
    * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    '''
        
    def addNFFG(self, nffg, user_id):
        """

        :param nffg:
        :param user_id:
        :type nffg: NF_FG
        :type user_id: str
        :return:
        """
            
        # New session id
        session_id = self.getNewUnivocalSessionID()
        
        # Add a new record in GraphSession
        self.dbStoreGraphSessionFromNffgObject(session_id, user_id, nffg)
    
        # [ ENDPOINTS ]
        for endpoint in nffg.end_points:
            
            # Add a new endpoint
            endpoint_id = self.dbStoreEndpoint(session_id, None, endpoint.id, endpoint.name, endpoint.type)
            endpoint.db_id = endpoint_id
            
            # Add end-point resources
            # End-point attached to something that is not another graph
            if endpoint.type == "interface" or endpoint.type == "vlan":
                self.addPort(session_id, endpoint_id, None, endpoint.interface, endpoint.node_id, endpoint.vlan_id, 'complete', None, None, None)
            elif endpoint.type == "gre-tunnel":
                self.addPort(session_id, endpoint_id, None, self.getNextGreInterfaceName(), Configuration().GRE_BRIDGE_ID, endpoint.vlan_id, 'complete', endpoint.local_ip, endpoint.remote_ip, endpoint.gre_key)

        # [ VNF ]
        for vnf in nffg.vnfs:
            domain_info = DomainInfo.get_from_file(Configuration().DOMAIN_DESCRIPTION_DYNAMIC_FILE)
            application_name = ""
            for functional_capability in domain_info.capabilities.functional_capabilities:
                if functional_capability.type == vnf.name:
                    application_name = functional_capability.name
            vnf_id = self.addVnf(session_id, None, vnf, nffg, application_name)
            vnf.db_id = vnf_id

        # [ FLOW RULES ]
        for flow_rule in nffg.flow_rules:
            self.addFlowrule(session_id, None, flow_rule, nffg)
            
        return session_id

    def updateNFFG(self, nffg, session_id):
        """

        :param nffg:
        :param session_id:
        :type nffg: NF_FG
        :return:
        """

        domain_info = DomainInfo.get_from_file(Configuration().DOMAIN_DESCRIPTION_DYNAMIC_FILE)

        # [ ENDPOINTS ]
        for endpoint in nffg.end_points:
            
            # Add a new endpoint
            if endpoint.status == 'new' or endpoint.status is None:
                endpoint_id = self.dbStoreEndpoint(session_id, None, endpoint.id, endpoint.name, endpoint.type)
                endpoint.db_id = endpoint_id

                # Add end-point resources
                # End-point attached to something that is not another graph
                if endpoint.type == "interface" or endpoint.type=="vlan":
                    self.addPort(session_id, endpoint_id, None, endpoint.interface, endpoint.node_id, endpoint.vlan_id, 'complete', None, None, None)
                elif endpoint.type == "gre-tunnel":
                    self.addPort(session_id, endpoint_id, None, self.getNextGreInterfaceName(), Configuration().GRE_BRIDGE_ID, endpoint.vlan_id, 'complete', endpoint.local_ip, endpoint.remote_ip, endpoint.gre_key)
        
        # [ FLOW RULES ]
        for flow_rule in nffg.flow_rules:
            if flow_rule.status == 'new' or flow_rule.status is None:
                self.addFlowrule(session_id, None, flow_rule, nffg)

        # [ VNF ]
        for vnf in nffg.vnfs:
            if vnf.status == 'new' or vnf.status is None:
                application_name = ""
                for functional_capability in domain_info.capabilities.functional_capabilities:
                    if functional_capability.type == vnf.name:
                        application_name = functional_capability.name
                vnf_id = self.addVnf(session_id, None, vnf, nffg, application_name)
                vnf.db_id = vnf_id

    def getNFFG(self, session_id):
        session = get_session()
        session_ref = session.query(GraphSessionModel).filter_by(session_id=session_id).one()
        
        # [ NF-FG ]
        nffg = NF_FG()
        #nffg.id = session_ref.graph_id
        nffg.name = session_ref.graph_name
        nffg.description = session_ref.description

        # [ ENDPOINTs ]
        end_points_ref = session.query(EndpointModel).filter_by(session_id=session_id).all()
        for end_point_ref in end_points_ref:
            
            # Add endpoint to NFFG
            end_point = EndPoint(_id=end_point_ref.graph_endpoint_id, name=end_point_ref.name, _type=end_point_ref.type, 
                                 db_id=end_point_ref.id)
            nffg.addEndPoint(end_point)
            
            # End_point resource
            end_point_resorces_ref = session.query(EndpointResourceModel).filter_by(endpoint_id=end_point_ref.id).all()
            for end_point_resorce_ref in end_point_resorces_ref:
                if end_point_resorce_ref.resource_type == 'port':
                    try:
                        port_ref = session.query(PortModel).filter_by(id=end_point_resorce_ref.resource_id).one()
                    except NoResultFound:
                        port_ref = None
                        logging.debug("Port not found for endpoint "+end_point_ref.graph_endpoint_id)
                    if port_ref is not None:
                        end_point.switch_id = port_ref.switch_id
                        end_point.interface = port_ref.graph_port_id
                        end_point.vlan_id = port_ref.vlan_id
                        end_point.node_id = port_ref.switch_id
                        end_point.local_ip = port_ref.ipv4_address
                        end_point.remote_ip = port_ref.tunnel_remote_ip
                        end_point.gre_key = port_ref.gre_key

        # [ VNFs ]
        vnfs_ref = session.query(VnfModel).filter_by(session_id=session_id).all()
        for vnf_ref in vnfs_ref:
            # add vnf to NFFG
            vnf = VNF(_id=vnf_ref.graph_vnf_id, name=vnf_ref.name, vnf_template_location=vnf_ref.template,
                      db_id=vnf_ref.id)
            nffg.addVNF(vnf)

            # vnf ports
            vnf_ports_ref = session.query(VnfPortModel).filter_by(vnf_id=vnf_ref.id).all()
            for vnf_port_ref in vnf_ports_ref:
                vnf_port = Port(_id=vnf_port_ref.graph_port_id, name=vnf_port_ref.name, db_id=vnf_port_ref.id)
                vnf.addPort(vnf_port)

        # [ FLOW RULEs ]
        flow_rules_ref = session.query(FlowRuleModel).filter_by(session_id=session_id).all()
        for flow_rule_ref in flow_rules_ref:
            if flow_rule_ref.type == 'external':  # None or 'external'
                continue
            
            # Add flow rule to NFFG
            flow_rule = FlowRule(_id=flow_rule_ref.graph_flow_rule_id, internal_id=flow_rule_ref.internal_id, 
                                 priority=int(flow_rule_ref.priority), description=flow_rule_ref.description, 
                                 db_id=flow_rule_ref.id)
            nffg.addFlowRule(flow_rule)

            # [ MATCHes ]
            try:
                match_ref = session.query(MatchModel).filter_by(flow_rule_id=flow_rule_ref.id).one()
            except NoResultFound:
                match_ref = None
                logging.debug("Found flowrule without a match")

            if match_ref is not None:
                # Retrieve port data
                port_in = None
                if match_ref.port_in_type == 'endpoint':
                    end_point_ref = session.query(EndpointModel).filter_by(id=match_ref.port_in).first()
                    port_in = 'endpoint:'+end_point_ref.graph_endpoint_id
                if match_ref.port_in_type == 'vnf':
                    port_in = match_ref.port_in
                
                # Add match to this flow rule
                match = Match(port_in=port_in, ether_type=match_ref.ether_type, vlan_id=match_ref.vlan_id,
                              vlan_priority=match_ref.vlan_priority, source_mac=match_ref.source_mac,
                              dest_mac=match_ref.dest_mac, source_ip=match_ref.source_ip, dest_ip=match_ref.dest_ip,
                              tos_bits=match_ref.tos_bits, source_port=match_ref.source_port, dest_port=match_ref.dest_port,
                              protocol=match_ref.protocol, db_id=match_ref.id)
                flow_rule.match = match

            # [ ACTIONs ]
            actions_ref = session.query(ActionModel).filter_by(flow_rule_id=flow_rule_ref.id).all()
            if len(actions_ref) == 0:
                logging.debug("Found flowrule without actions")
                
            for action_ref in actions_ref:
                output_to_port = None
                # Retrieve endpoint data
                if action_ref.output_type == 'endpoint':
                    end_point_ref = session.query(EndpointModel).filter_by(id = action_ref.output_to_port).first()
                    output_to_port = action_ref.output_type+':'+end_point_ref.graph_endpoint_id
                if action_ref.output_type == 'vnf':
                    output_to_port = action_ref.output_to_port

                # Add action to this flow rule
                action = Action(output=output_to_port, controller=action_ref.output_to_controller, drop=action_ref._drop, 
                                set_vlan_id=action_ref.set_vlan_id, set_vlan_priority=action_ref.set_vlan_priority, 
                                push_vlan=action_ref.push_vlan, pop_vlan=action_ref.pop_vlan, 
                                set_ethernet_src_address=action_ref.set_ethernet_src_address, 
                                set_ethernet_dst_address=action_ref.set_ethernet_dst_address, 
                                set_ip_src_address=action_ref.set_ip_src_address, set_ip_dst_address=action_ref.set_ip_dst_address, 
                                set_ip_tos=action_ref.set_ip_tos, set_l4_src_port=action_ref.set_l4_src_port, 
                                set_l4_dst_port=action_ref.set_l4_dst_port, output_to_queue=action_ref.output_to_queue,
                                db_id=action_ref.id)
                flow_rule.actions.append(action)
        
        return nffg    

    def getAllNFFG(self):
        session = get_session()
        session_refs = session.query(GraphSessionModel).all()
        nffgs = []
        for session in session_refs:
            if session.status == 'complete':
                nffg = {}
                nffg['graph_id'] = session.graph_id
                nffg['graphDict'] = self.getNFFG(session.session_id)
                nffgs.append(nffg)
        return nffgs

    def getNFFG_id(self, nffg_id):
        session = get_session()
        return session.query(GraphSessionModel.graph_id).filter_by(graph_id=nffg_id).all()

    def get_nffg_id_by_session(self, session_id):
        session = get_session()
        return session.query(GraphSessionModel).filter_by(session_id=session_id).one()
