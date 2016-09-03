'''
Created on 2/feb/2016

@author: giacomoratta
'''
import requests, logging
from do_core.controller_interface.rest import RestInterface


class ONOS_Rest(RestInterface):
    
    version=""
    
    def __init__(self, version):
        self.version=version
        
        self.rest_devices_url = '/onos/v1/devices'
        self.rest_links_url = '/onos/v1/links'
        self.rest_flows_url = '/onos/v1/flows'  # /onos/v1/flows/{DeviceId}
        self.rest_apps_url = '/onos/v1/applications'

    def __logging_debug(self, response, url, jsonFlow=None):
        log_string = "response: "+str(response.status_code)+", "+response.reason
        log_string = url+"\n"+log_string
        if jsonFlow is not None:
            log_string = log_string+"\n"+jsonFlow
        logging.debug(log_string)

    def getDevices(self, onos_endpoint, onos_user, onos_pass):
        headers = {'Accept': 'application/json'}
        url = onos_endpoint+self.rest_devices_url
    
        response = requests.get(url, headers=headers, auth=(onos_user, onos_pass))
        
        self.__logging_debug(response, url)
        response.raise_for_status()
        return response.text

    def getLinks(self, onos_endpoint, onos_user, onos_pass):
        headers = {'Accept': 'application/json'}
        url = onos_endpoint+self.rest_links_url
    
        response = requests.get(url, headers=headers, auth=(onos_user, onos_pass))
        
        self.__logging_debug(response, url)
        response.raise_for_status()
        return response.text

    def getDevicePorts(self, onos_endpoint, onos_user, onos_pass, switch_id):
        headers = {'Accept': 'application/json'}
        url = onos_endpoint+self.rest_devices_url+"/"+str(switch_id)+"/ports"

        response = requests.get(url, headers=headers, auth=(onos_user, onos_pass))

        self.__logging_debug(response, url)
        response.raise_for_status()
        return response.text

    def createFlow(self, onos_endpoint, onos_user, onos_pass, jsonFlow, switch_id):
        '''
        Create a flow on the switch selected (Currently using OF1.0)
        Args:
            jsonFlow:
                JSON structure which describes the flow specifications
            switch_id:
                ONOS id of the switch (example: of:1234567890)
            flow_id:
                OpenFlow id of the flow
        Exceptions:
            raise the requests.HTTPError exception connected to the REST call in case of HTTP error
        '''
        headers = {'Accept': 'application/json', 'Content-type':'application/json'}
        url = onos_endpoint+self.rest_flows_url+"/"+str(switch_id)
        response = requests.post(url,jsonFlow,headers=headers, auth=(onos_user, onos_pass))
        
        self.__logging_debug(response, url, jsonFlow)
        response.raise_for_status()
        
        location = str(response.headers['location']).split("/")
        flow_id = location[len(location)-1] 
        
        return flow_id, response.text

    def deleteFlow(self, onos_endpoint, onos_user, onos_pass, switch_id, flow_id):
        '''
        Delete a flow
        Args:
            switch_id:
                ONOS id of the switch (example: of:1234567890)
            flow_id:
                OpenFlow id of the flow
        Exceptions:
            raise the requests.HTTPError exception connected to the REST call in case of HTTP error
        '''
        # headers = {'Accept': 'application/json', 'Content-type':'application/json'}
        headers = {'Accept': 'application/json'}
        url = onos_endpoint+self.rest_flows_url+"/"+str(switch_id)+"/"+str(flow_id)
        response = requests.delete(url,headers=headers, auth=(onos_user, onos_pass))
        
        self.__logging_debug(response, url)
        response.raise_for_status()
        return response.text

    def activateApp(self, onos_endpoint, onos_user, onos_pass, app_name):
        """
        Activate an application on top of the controller
        :param onos_endpoint: controller REST API address
        :param onos_user: controller user
        :param onos_pass: controller password for user
        :param app_name: the application to activate
        :return:
        """
        headers = {'Accept': 'application/json'}
        url = onos_endpoint+self.rest_apps_url+"/"+str(app_name)+"/active"
        response = requests.post(url, headers=headers, auth=(onos_user, onos_pass))

        self.__logging_debug(response, url)
        response.raise_for_status()
        return response.text

    def deactivateApp(self, onos_endpoint, onos_user, onos_pass, app_name):
        """
        Deactivate an application running on top of the controller
        :param onos_endpoint: controller REST API address
        :param onos_user: controller user
        :param onos_pass: controller password for user
        :param app_name: the application to activate
        :return:
        """
        headers = {'Accept': 'application/json'}
        url = onos_endpoint+self.rest_apps_url+"/"+str(app_name)+"/active"
        response = requests.delete(url, headers=headers, auth=(onos_user, onos_pass))

        self.__logging_debug(response, url)
        response.raise_for_status()
        return response.text



