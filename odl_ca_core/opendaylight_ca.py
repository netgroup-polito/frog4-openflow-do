'''
@author: fabiomignini
@author: vida
@author: giacomoratta
'''

from __future__ import division
from __builtin__ import str
import logging, json

from nffg_library.nffg import FlowRule

from odl_ca_core.sql.graph_session import GraphSession


from odl_ca_core.config import Configuration
from odl_ca_core.odl_rest import ODL_Rest
from odl_ca_core.resources import Action, Match, Flow, ProfileGraph, Endpoint
from odl_ca_core.netgraph import NetGraph
from odl_ca_core.exception import sessionNotFound, GraphError, NffgUselessInformations






class OpenDayLightCA(object):

    def __init__(self, user_data):
        
        conf = Configuration()
        
        self._session_id = None
        
        self.nffg = None
        self.user_data = user_data
        '''
        Fields:
         - user_data.username
         - user_data.password
         - user_data.tenant
        '''
        
        # Dati ODL
        self.odlendpoint = conf.ODL_ENDPOINT
        self.odlversion = conf.ODL_VERSION
        self.odlusername = conf.ODL_USERNAME
        self.odlpassword = conf.ODL_PASSWORD
        
        # NetGraph
        self.netgraph = NetGraph(self.odlversion, self.odlendpoint, self.odlusername, self.odlpassword)



    def NFFG_Put(self, nffg):
        '''
        Manage the request of NF-FG instantiation
        '''
        logging.debug("Put NF-FG: put from user "+self.user_data.username+" on tenant "+self.user_data.tenant)
        
        # Check if the NF-FG is already instantiated, update it and exit
        if self.NFFG_Update(nffg) is not None:
            return self._session_id
            
        # Instantiate a new NF-FG
        try:
            self._session_id = GraphSession().addNFFG(nffg, self.user_data.getUserID())
            logging.debug("Put NF-FG: instantiating a new nffg: " + nffg.getJSON(True))
            
            # Profile graph for ODL functions
            profile_graph = self._ProfileGraph_BuildFromNFFG(nffg)
            
            # Write latest info in the database and send all the flow rules to ODL
            self._ODL_FlowsInstantiation(profile_graph)
            
            logging.debug("Put NF-FG: session " + self._session_id + " correctly instantiated!")

        except Exception as ex:
            logging.error(ex.message)
            logging.exception(ex.message)
            GraphSession().deleteGraph(self._session_id)
            GraphSession().setErrorStatus(self._session_id)
            raise ex
        
        GraphSession().updateStatus(self._session_id, 'complete')                                
        return self._session_id

    
    
    def NFFG_Update(self, new_nffg):

        # Check and get the session id for this user-graph couple
        logging.debug("Update NF-FG: check if the user "+self.user_data.getUserID()+" has already instantiated the graph "+new_nffg.id+".")
        session = GraphSession().getActiveSession(self.user_data.getUserID(), new_nffg.id, error_aware=True)
        if session is None:
            return None
        self._session_id = session.session_id
        
        logging.debug("Update NF-FG: already instantiated, trying to update it")
        logging.debug("Update NF-FG: updating session "+self._session_id+" from user "+self.user_data.username+" on tenant "+self.user_data.tenant)
        GraphSession().updateStatus(self._session_id, 'updating')

        # Get the old NFFG
        old_nffg = GraphSession().getNFFG(self._session_id)
        logging.debug("Update NF-FG: the old session: "+old_nffg.getJSON())
        
        # TODO: remove or integrate remote_graph and remote_endpoint

        try:
            updated_nffg = old_nffg.diff(new_nffg)
            logging.debug("Update NF-FG: coming updates: "+updated_nffg.getJSON(True))            
            
            # Delete useless endpoints and flowrules 
            self._ODL_FlowsControlledDeletion(updated_nffg)
            
            # Update database and send flowrules to ODL
            GraphSession().updateNFFG(updated_nffg, self._session_id)
            profile_graph = self._ProfileGraph_BuildFromNFFG(updated_nffg)
            self._ODL_FlowsInstantiation(profile_graph)
            
            logging.debug("Update NF-FG: session " + self._session_id + " correctly updated!")
            
        except Exception as ex:
            logging.error("Update NF-FG: "+ex.message)
            logging.exception("Update NF-FG: "+ex.message)
            # TODO: discuss... delete the graph when an error occurs in this phase?
            #GraphSession().deleteGraph(self._session_id)
            #GraphSession().setErrorStatus(self._session_id)
            raise ex
        
        GraphSession().updateStatus(self._session_id, 'complete')
        return self._session_id
    
    
    
    def NFFG_Delete(self, nffg_id):
        
        session = GraphSession().getActiveSession(self.user_data.getUserID(), nffg_id, error_aware=False)
        if session is None:
            raise sessionNotFound("Delete NF-FG: session not found for graph "+str(nffg_id))
        
        self._session_id = session.session_id
        
        logging.debug("Delete NF-FG: deleting session "+str(self._session_id))

        instantiated_nffg = GraphSession().getNFFG(self._session_id)
        logging.debug("Delete NF-FG: we are going to delete: "+instantiated_nffg.getJSON())
    
        try:
            self._ODL_FlowsDeletion(self._session_id)
            logging.debug("Delete NF-FG: session " + self._session_id + " correctly deleted!")
            
        except Exception as ex:
            logging.error("Delete NF-FG: "+ex.message)
            logging.exception("Delete NF-FG: "+ex.message)
            #raise ex - no raise because we need to delete the session in any case
        GraphSession().deleteGraph(self._session_id)
        GraphSession().setEnded(self._session_id)



    def NFFG_Get(self, nffg_id):
        session = GraphSession().getActiveSession(self.user_data.getUserID(), nffg_id, error_aware=False)
        if session is None:
            raise sessionNotFound("Get NF-FG: session not found, for graph "+str(nffg_id))
        
        self._session_id = session.session_id
        logging.debug("Getting session: "+str(self._session_id))
        return GraphSession().getNFFG(self._session_id).getJSON()



    def NFFG_Status(self, nffg_id):
        session = GraphSession().getActiveSession(self.user_data.getUserID(),nffg_id,error_aware=True)
        if session is None:
            raise sessionNotFound("Status NF-FG: session not found, for graph "+str(nffg_id))
        
        self._session_id = session.session_id
        logging.debug("Status NF-FG: graph status: "+str(session.status))
        return session.status
    
    
    
    def NFFG_Validate(self, nffg):
        '''
        A validator for this specific control adapter.
        The original json, as specified in the extern NFFG library,
        could contain useless objects and fields for this CA.
        If this happens, we have to raise exceptions to stop the request processing.  
        '''        
        if len(nffg.vnfs)>0:
            msg = "NFFG: presence of 'VNFs'. This CA does not process this information."
            logging.debug(msg)
            raise NffgUselessInformations(msg)
        
        for ep in nffg.end_points:
            if(ep.remote_endpoint_id is not None):
                msg = "NFFG: presence of 'end-points.remote_endpoint_id'. This CA does not process this information."
                logging.debug(msg)
                raise NffgUselessInformations(msg)
            if(ep.remote_ip is not None):
                msg = "NFFG: presence of 'end-points.remote-ip'. This CA does not process this information."
                logging.debug(msg)
                raise NffgUselessInformations(msg)
            if(ep.type <> "interface"):
                msg = "NFFG: 'end-points.type' must be 'interface'."
                logging.debug(msg)
                raise NffgUselessInformations(msg)



    def _ProfileGraph_BuildFromNFFG(self, nffg):
        '''
        Create a ProfileGraph with the flowrules and endpoints specified in nffg.
        Args:
            nffg:
                Object of the Class Common.NF_FG.nffg.NF_FG
        Return:
            Object of the Class odl_ca_core.resources.ProfileGraph
        '''
        profile_graph = ProfileGraph()

        for endpoint in nffg.end_points:
            
            if endpoint.status is None:
                status = "new"
            else:
                status = endpoint.status

            # TODO: remove or integrate 'remote_endpoint' code
            
            ep = Endpoint(endpoint.id, endpoint.name, endpoint.type, endpoint.vlan_id, endpoint.switch_id, endpoint.interface, status)
            profile_graph.addEndpoint(ep)
        
        for flowrule in nffg.flow_rules:
            if flowrule.status is None:
                flowrule.status = 'new'
            profile_graph.addFlowrule(flowrule)
                  
        return profile_graph




     
    '''
    ######################################################################################################
    #########################    Interactions with OpenDaylight              #############################
    ######################################################################################################
    '''
        
    def _ODL_FlowsInstantiation(self, profile_graph):
        
        # Create the endpoints
        # for endpoint in profile_graph.endpoints.values():
        #    if endpoint.status == "new":
                # TODO: remove or integrate remote_graph and remote_endpoint

        # Create and push the flowrules
        for flowrule in profile_graph.flowrules.values():
            if flowrule.status =='new':
                
                #TODO: check priority
                
                if flowrule.match is not None:
                    if flowrule.match.port_in is not None:
                        
                        tmp1 = flowrule.match.port_in.split(':')
                        port1_type = tmp1[0]
                        port1_id = tmp1[1]
                        
                        if port1_type == 'endpoint':
                            endp1 = profile_graph.endpoints[port1_id]
                            if endp1.type == 'interface':        
                                self._ODL_ProcessFlowrule(endp1, flowrule, profile_graph)



    def _ODL_FlowsDeletion(self, session_id):       
        #Delete every flow from ODL
        flows = GraphSession().getFlowrules(session_id)
        for flow in flows:
            if flow.type == "external" and flow.status == "complete":
                ODL_Rest(self.odlversion).deleteFlow(self.odlendpoint, self.odlusername, self.odlpassword, flow.switch_id, flow.internal_id)



    def _ODL_FlowsControlledDeletion(self, updated_nffg):
        
        # Delete the endpoints 'to_be_deleted'
        for endpoint in updated_nffg.end_points[:]:
            if endpoint.status == 'to_be_deleted':
                
                # TODO: remove or integrate remote_graph, remote_endpoint, endpoint_resource "flowrule", and graph_connection
                
                # Delete endpoints and all resourcess associated to it.
                GraphSession().deleteEndpoint(endpoint.id, self._session_id)
                GraphSession().deleteEndpointResourceAndResources(endpoint.db_id)
                
                updated_nffg.end_points.remove(endpoint)  
        
        # Delete the flowrules 'to_be_deleted'              
        for flowrule in updated_nffg.flow_rules[:]:
            if flowrule.status == 'to_be_deleted' and flowrule.type != 'external':
                
                # Get and delete the flow rules with the same flow.internal_id,
                # which are the flow rules effectively pushed in ODL.
                flows = GraphSession().getFlowrules(self._session_id)
                for flow in flows:
                    if flow.type == "external" and flow.status == "complete" and flow.internal_id == flowrule.id:
                        ODL_Rest(self.odlversion).deleteFlow(self.odlendpoint, self.odlusername, self.odlpassword, flow.switch_id, flow.graph_flow_rule_id)
                        GraphSession().deleteFlowrule(flow.id)
                
                # Finally, delete the main flow rule (that written in nffg.json)
                GraphSession().deleteFlowrule(flowrule.db_id)
                updated_nffg.flow_rules.remove(flowrule)
    




    class ___processedFLowrule(object):
            
        def __init__(self,switch_id=None,match=None,actions=None,flow_id=None,priority=None,flowname_suffix=None):
            self.switch_id = switch_id
            self.match = match
            if actions is None:
                self.actions = []
            else:
                self.actions = actions
            self.flow_id = flow_id
            self.flow_name = str(flow_id)+"_"
            if flowname_suffix is not None:
                self.flow_name = self.flow_name + flowname_suffix
            self.priority = priority
        
        def setFr1(self, switch_id, action, port_in, port_out, flowname_suffix):
            if(self.match is None):
                self.match = Match()
            new_act = Action(action)
            if(port_out is not None):
                new_act.setOutputAction(port_out, 65535)
            
            self.actions.append(new_act)
            self.match.setInputMatch(port_in)
            self.switch_id = switch_id
            self.flow_name = self.flow_name+flowname_suffix
        
        def isReady(self):
            return ( self.switch_id is not None and self.flow_id is not None )




    def _ODL_ProcessFlowrule(self, endpoint1, flowrule, profile_graph):
        #Process a flow rule written in the section "big switch" of a nffg json.
        
        fr1 = OpenDayLightCA.___processedFLowrule(match=Match(flowrule.match),
                                                  priority=flowrule.priority,
                                                  flow_id=flowrule.id)
        
        fr2 = OpenDayLightCA.___processedFLowrule(priority=flowrule.priority,
                                                  flow_id=flowrule.id)

           
        nodes_path = None
        nodes_path_flag = None
        
        print "\n\n\nodlProcessFlowrule"
        
        # Add "Drop" flow rules only, and return.
        # If a flow rule has a drop action, we don't care other actions!
        for a in flowrule.actions:
            if a.drop is True:
                fr1.setFr1(endpoint1.switch_id, a, endpoint1.interface , None, "1")
                self._ODL_PushFlow(fr1)
                return  
        
        # Split the action handling in output and non-output.
        for a in flowrule.actions:
            
            # If this action is not an output action,
            # we just append it to the final actions list 'actions1'.
            if a.output is None:
                #new_act = Action(a)
                #actions1.append(new_act)
                fr1.actions.append(Action(a))
            
            # If this action is an output action (a.output is not None),
            # we check that the output is an endpoint and manage the main cases.
            else:
                
                # Is the 'output' destination an endpoint?
                tmp2 = a.output.split(':')
                port2_type = tmp2[0]
                port2_id = tmp2[1]
                if port2_type == 'endpoint':
                    endpoint2 = profile_graph.endpoints[port2_id]
                    
                    # Endpoints are on the same switch
                    if endpoint1.switch_id == endpoint2.switch_id:
                        
                        # Error: endpoints are equal!
                        if endpoint1.interface == endpoint2.interface:
                            raise GraphError("Flowrule "+flowrule.id+" is wrong: endpoints are overlapping")
                        
                        # Install a flow between two ports of the switch
                        else:
                            fr1.setFr1(endpoint1.switch_id, a, endpoint1.interface , endpoint2.interface, "1")
                    
                    # Endpoints are on different switches              
                    else:
                        
                        # Check if a link between endpoint switches exists.
                        # Return: port12 (on endpoint1 switch) and port21 (on endpoint2 switch).
                        port12,port21 = self._ODL_GetLinkPortsBetweenSwitches(endpoint1.switch_id, endpoint2.switch_id)       
                        
                        # A link between endpoint switches exists!
                        if port12 is not None and port21 is not None:
                            
                            # Endpoints are not on the link: 2 flows 
                            if endpoint1.interface != port12 and endpoint2.interface != port21:
                                fr1.setFr1(endpoint1.switch_id, a, endpoint1.interface , port12, "1")
                                fr2.setFr1(endpoint2.switch_id, None, port21 , endpoint2.interface, "2")
                            
                            # Flow installed on first switch
                            elif endpoint1.interface != port12 and endpoint2.interface == port21:
                                fr1.setFr1(endpoint1.switch_id, a, endpoint1.interface , port12, "1")
                                                                
                            # Flow installed on second switch                                
                            elif endpoint1.interface == port12 and endpoint2.interface != port21:
                                fr1.setFr1(endpoint2.switch_id, a, endpoint2.interface , port21, "2")
                            
                            # Endpoints are on the link: cannot install flow
                            elif endpoint1.interface == port12 and endpoint2.interface == port21:
                                logging.warning("Flow not installed for flowrule id "+flowrule.id+ ": both endpoints are on the same link")
                        
                        # No link between endpoint switches...search for a path!
                        else:
                            if(nodes_path_flag == None):
                                self.netgraph.getTopologyGraph()
                                nodes_path = self.netgraph.getShortestPath(endpoint1.switch_id, endpoint2.switch_id)
                                nodes_path_flag = 1
                            
                            if(nodes_path == None):
                                logging.debug("Cannot find a link between "+endpoint1.switch_id+" and "+endpoint2.switch_id)
                            else:
                                logging.debug("Creating a path bewteen "+endpoint1.switch_id+" and "+endpoint2.switch_id+". "+
                                              "Path Length = "+str(len(nodes_path)))
                        
        
        # Push the fr1, if it is ready                
        if fr1.isReady():
            self._ODL_PushFlow(fr1)
        
            # Push the fr2, if it is ready     
            if fr2.isReady():
                self._ODL_PushFlow(fr2)
        
        # There is a path between the two endpoint
        if(nodes_path_flag is not None and nodes_path is not None):
            self._ODL_LinkEndpoints(nodes_path, endpoint1, endpoint2, flowrule)

                
    
    # TODO: eliminate this function
    def _ODL_PushFlow2(self, switch_id, actions, match, flowname, priority, flow_id, suffix):
        pfr = OpenDayLightCA.___processedFLowrule(switch_id=switch_id, match=match, actions=actions, flow_id=flow_id, priority=priority, flowname_suffix=suffix)
        self._ODL_PushFlow(pfr)
    
    
    
    def _ODL_PushFlow(self, pfr):
        # pfr = ___processedFLowrule

        # ODL/Switch: Add flow rule
        flowj = Flow("flowrule", pfr.flow_name, 0, pfr.priority, True, 0, 0, pfr.actions, pfr.match)
        json_req = flowj.getJSON(self.odlversion, pfr.switch_id)
        ODL_Rest(self.odlversion).createFlow(self.odlendpoint, self.odlusername, self.odlpassword, json_req, pfr.switch_id, pfr.flow_name)
        
        # DATABASE: Add flow rule
        flow_rule = FlowRule(_id=pfr.flow_id,node_id=pfr.switch_id, _type='external', status='complete',priority=pfr.priority, internal_id=pfr.flow_name)  
        GraphSession().addFlowrule(self._session_id, pfr.switch_id, flow_rule, None)
        
    
    
    def _ODL_GetLinkBetweenSwitches(self, switch1, switch2):             
        '''
        Retrieve the link between two switches, where you can find ports to use.
        switch1, switch2 = "openflow:123456789" or "00:00:64:e9:50:5a:90:90" in Hydrogen.
        '''
        
        # Get Topology
        json_data = ODL_Rest(self.odlversion).getTopology(self.odlendpoint, self.odlusername, self.odlpassword)
        topology = json.loads(json_data)
        
        if self.odlversion == "Hydrogen":
            tList = topology["edgeProperties"]
            for link in tList:
                source_node = link["edge"]["headNodeConnector"]["node"]["id"]
                dest_node = link["edge"]["tailNodeConnector"]["node"]["id"]
                if (source_node == switch1 and dest_node == switch2):
                    return link
        else:
            tList = topology["network-topology"]["topology"][0]["link"]
            for link in tList:
                source_node = link["source"]["source-node"]
                dest_node = link["destination"]["dest-node"]
                if (source_node == switch1 and dest_node == switch2):
                    return link
        return None


    
    def _ODL_GetLinkPortsBetweenSwitches(self, switch1, switch2):
        link = self._ODL_GetLinkBetweenSwitches(switch1, switch2)
        if link is None:
            return None,None
        
        if self.odlversion == "Hydrogen":
            port12 = link["edge"]["headNodeConnector"]["id"]
            port21 = link["edge"]["tailNodeConnector"]["id"]
        else:
            tmp = link["source"]["source-tp"]
            tmpList = tmp.split(":")
            port12 = tmpList[2]

            tmp = link["destination"]["dest-tp"]
            tmpList = tmp.split(":")
            port21 = tmpList[2]
        
        # Return port12@switch1 and port21@switch2
        return port12,port21



    def _ODL_LinkEndpoints(self,path,ep1,ep2,flowrule):

        flow_id = flowrule.id
        flow_priority = flowrule.priority
        actions = []
        vlan_id = None
        
        print ""
        print "Flow id: "+str(flow_id)
        print "Flow priority: "+str(flow_priority)        
        
        
        # Clean actions
        for a in flowrule.actions:
            
            # Store the VLAN ID and remove the action
            if a.set_vlan_id is not None:
                vlan_id = a.set_vlan_id
                continue
            
            # Filter non OUTPUT actions 
            if a.output is None:
                action = Action(a)
                actions.append(action)
                
        
        #TODO: Keep track of all vlan ID
        if vlan_id is not None:
            '''
                - controlla se l'id e' gia' usato nella rete
                - eventualmente ne recupera un'altro
                - vlan_id = <nuovo vlan id>
                
                quando viene richiesto di collegare due endpoint lontani
                la prima soluzione e' lavorare con le vlan; ma l'id della vlan
                sarebbe meglio che non venisse specificato nel grafo, ma che 
                fosse deciso automaticamente comunicandolo infine a chi ha fatto
                la richiesta originale del collegamento dei due endpoint.
                
            '''
            print ""
        
        
        # Traverse the path and create the flow for each switch
        for i in range(0, len(path)):
            hop = path[i]
            
            match = Match(flowrule.match)
            new_actions = list(actions)
            
            if i==0:
                #first switch
                switch_id = ep1.switch_id
                port_in = ep1.interface
                port_out = self.netgraph.topology[hop][path[i+1]]['from_port']
                
                if vlan_id is not None:
                    action_pushvlan = Action()
                    action_pushvlan.setPushVlanAction()
                    new_actions.append(action_pushvlan)
                    
                    action_setvlan = Action()
                    action_setvlan.setSwapVlanAction(vlan_id)
                    new_actions.append(action_setvlan)
                
            elif i==len(path)-1:
                #last switch
                switch_id = ep2.switch_id
                port_in = self.netgraph.topology[path[i-1]][hop]['to_port']
                port_out = ep2.interface
                
                if vlan_id is not None:
                    match.setVlanMatch(vlan_id)
                    action_stripvlan = Action()
                    action_stripvlan.setPopVlanAction()
                    new_actions.append(action_stripvlan)

            else:
                #middle way switch
                switch_id = hop
                port_in = self.netgraph.topology[path[i-1]][hop]['to_port']
                port_out = self.netgraph.topology[hop][path[i+1]]['from_port']
                
                if vlan_id is not None:
                    match.setVlanMatch(vlan_id)
                
            print switch_id+" from "+str(port_in)+" to "+str(port_out)
            
            match.setInputMatch(port_in)
            
            action_output = Action()
            action_output.setOutputAction(port_out, 65535)
            new_actions.append(action_output)
            
            flow_name = str(flow_id)+"_"+str(i)
            
            # TODO: use _ODL_PushFlow and create the object ___processedFlowRule
            self._ODL_PushFlow2(switch_id, new_actions, match, flow_name, flow_priority, flow_id, str(i))
        
        return

