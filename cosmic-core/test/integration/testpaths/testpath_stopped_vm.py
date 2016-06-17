# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
""" Test Path for Deploy VM in stopped state
"""
import time
from marvin.cloudstackTestCase import cloudstackTestCase
from marvin.codes import (PASS,
                          STOPPED,
                          RUNNING)
from marvin.lib.base import (Account,
                             ServiceOffering,
                             VirtualMachine,
                             User,
                             Network,
                             Router,
                             Volume,
                             Iso,
                             Template)
from marvin.lib.common import (get_domain,
                               get_zone,
                               get_template,
                               createEnabledNetworkOffering,
                               wait_for_cleanup)
from marvin.lib.utils import (cleanup_resources,
                              validateList)
from marvin.sshClient import SshClient
from nose.plugins.attrib import attr


def VerifyChangeInServiceOffering(self, virtualmachine, serviceoffering):
    """List the VM and verify that the new values for cpuspeed,
       cpunumber and memory match with the new service offering"""

    exceptionOccured = False
    exceptionMessage = ""
    try:
        vmlist = VirtualMachine.list(self.userapiclient, id=virtualmachine.id)
        self.assertEqual(
            validateList(vmlist)[0],
            PASS,
            "vm list validation failed")
        vm = vmlist[0]

        # Verify the custom values
        self.assertEqual(str(vm.cpunumber), str(serviceoffering.cpunumber),
                         "vm cpu number %s not matching with cpu number in\
                      service offering %s" %
                         (vm.cpunumber, serviceoffering.cpunumber))

        self.assertEqual(str(vm.cpuspeed), str(serviceoffering.cpuspeed),
                         "vm cpu speed %s not matching with cpu speed in\
                     service offering %s" %
                         (vm.cpuspeed, serviceoffering.cpuspeed))

        self.assertEqual(str(vm.memory), str(serviceoffering.memory),
                         "vm memory %s not matching with memory in\
                     service offering %s" %
                         (vm.memory, serviceoffering.memory))
    except Exception as e:
        exceptionOccured = True
        exceptionMessage = e
    return [exceptionOccured, exceptionMessage]


def VerifyRouterState(apiclient, account, domainid, desiredState,
                      retries=0):
    """List the router associated with the account and
       verify that router state matches with the desired state
       Return PASS/FAIL depending upon whether router state matches
       or not"""

    isRouterStateDesired = False
    failureMessage = ""
    while retries >= 0:
        routers = Router.list(
            apiclient,
            account=account,
            domainid=domainid,
            listall=True
        )
        if str(routers[0].state).lower() == str(desiredState).lower():
            isRouterStateDesired = True
            break
        time.sleep(60)
        retries -= 1
    # whileEnd

    if not isRouterStateDesired:
        failureMessage = "Router state should be %s,\
                but it is %s" % \
                         (desiredState, routers[0].state)
    return [isRouterStateDesired, failureMessage]


def CreateEnabledNetworkOffering(apiclient, networkServices):
    """Create network offering of given services and enable it"""

    result = createEnabledNetworkOffering(apiclient, networkServices)
    assert result[0] == PASS, \
        "Network offering creation/enabling failed due to %s" % result[2]
    return result[1]


class TestAdvancedZoneStoppedVM(cloudstackTestCase):
    @classmethod
    def setUpClass(cls):
        testClient = super(TestAdvancedZoneStoppedVM, cls).getClsTestClient()
        cls.apiclient = testClient.getApiClient()
        cls.testdata = testClient.getParsedTestDataConfig()
        cls.hypervisor = testClient.getHypervisorInfo()
        # Get Zone, Domain and templates
        cls.domain = get_domain(cls.apiclient)
        cls.zone = get_zone(cls.apiclient)
        cls._cleanup = []

        try:
            # Create an account
            cls.account = Account.create(
                cls.apiclient,
                cls.testdata["account"],
                domainid=cls.domain.id
            )
            cls._cleanup.append(cls.account)

            # If local storage is enabled, alter the offerings to use
            # localstorage
            if cls.zone.localstorageenable:
                cls.testdata["service_offering"]["storagetype"] = 'local'

            # Create 2 service offerings with different values for
            # for cpunumber, cpuspeed, and memory

            cls.testdata["service_offering"]["cpunumber"] = 1
            cls.testdata["service_offering"]["cpuspeed"] = 128
            cls.testdata["service_offering"]["memory"] = 256

            cls.service_offering = ServiceOffering.create(
                cls.apiclient,
                cls.testdata["service_offering"]
            )
            cls._cleanup.append(cls.service_offering)

            cls.testdata["service_offering"]["cpunumber"] = 2

            cls.service_offering_2 = ServiceOffering.create(
                cls.apiclient,
                cls.testdata["service_offering"]
            )
            cls._cleanup.append(cls.service_offering_2)

            # Create isolated network offering
            cls.isolated_network_offering = CreateEnabledNetworkOffering(
                cls.apiclient,
                cls.testdata["isolated_network_offering"]
            )
            cls._cleanup.append(cls.isolated_network_offering)

            cls.networkid = None
            if str(cls.zone.networktype).lower() == "advanced":
                cls.network = Network.create(
                    cls.apiclient, cls.testdata["isolated_network"],
                    networkofferingid=cls.isolated_network_offering.id,
                    accountid=cls.account.name,
                    domainid=cls.account.domainid,
                    zoneid=cls.zone.id)
                cls.networkid = cls.network.id

            # Create user api client of the account
            cls.userapiclient = testClient.getUserApiClient(
                UserName=cls.account.name,
                DomainName=cls.account.domain
            )

            template = get_template(
                cls.apiclient,
                cls.zone.id,
                cls.testdata["ostype"])
            cls.defaultTemplateId = template.id
            # Set Zones and disk offerings

            # Check that we are able to login to the created account
            respose = User.login(
                cls.apiclient,
                username=cls.account.name,
                password=cls.testdata["account"]["password"]
            )

            assert respose.sessionkey is not None, \
                "Login to the CloudStack should be successful\
                            response shall have non Null key"

        except Exception as e:
            cls.tearDownClass()
            raise e
        return

    @classmethod
    def tearDownClass(cls):
        try:
            cleanup_resources(cls.apiclient, cls._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.cleanup = []

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
            # Wait for Router cleanup before runnign further test case
            wait_for_cleanup(
                self.apiclient, [
                    "network.gc.interval", "network.gc.wait"])
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @attr(tags=["advanced", "basic"], required_hardware="True")
    def test_01_pt_deploy_vm_without_startvm(self):
        """ Positive test for stopped VM test path - T1

        # 1.  Deploy VM in the network without specifying startvm parameter
        # 2.  List VMs and verify that VM is in running state
        # 3.  Verify that router is in running state (Advanced zone)
        # 4.  Add network rules for VM (done in base.py itself) to make
        #     it accessible
        # 5.  Verify that VM is accessible
        # 6.  Destroy and expunge the VM
        # 7.  Wait for network gc time interval and check that router is
        #     in Stopped state
        """
        # Create VM in account
        virtual_machine = VirtualMachine.create(
            self.userapiclient,
            self.testdata["small"],
            templateid=self.defaultTemplateId,
            accountid=self.account.name,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            networkids=[self.networkid, ] if self.networkid else None,
            zoneid=self.zone.id,
            mode=self.zone.networktype
        )

        response = virtual_machine.getState(
            self.userapiclient,
            VirtualMachine.RUNNING)
        self.assertEqual(response[0], PASS, response[1])

        if str(self.zone.networktype).lower() == "advanced":
            response = VerifyRouterState(
                self.apiclient,
                self.account.name,
                self.account.domainid,
                RUNNING
            )
            self.assertTrue(response[0], response[1])

        # Check VM accessibility
        try:
            SshClient(host=virtual_machine.ssh_ip,
                      port=self.testdata["natrule"]["publicport"],
                      user=virtual_machine.username,
                      passwd=virtual_machine.password)
        except Exception as e:
            self.fail("Exception while SSHing to VM: %s" % e)

        virtual_machine.delete(self.apiclient)

        if str(self.zone.networktype).lower() == "advanced":
            # Wait for router to go into stopped state
            wait_for_cleanup(
                self.apiclient, [
                    "network.gc.interval", "network.gc.wait"])

            response = VerifyRouterState(
                self.apiclient,
                self.account.name,
                self.account.domainid,
                STOPPED,
                retries=10
            )
            self.assertTrue(response[0], response[1])
        return

    @attr(tags=["advanced", "basic"], required_hardware="True")
    def test_02_pt_deploy_vm_with_startvm_true(self):
        """ Positive test for stopped VM test path - T1 variant

        # 1.  Deploy VM in the network specifying startvm parameter as True
        # 2.  List VMs and verify that VM is in running state
        # 3.  Verify that router is in running state (Advanced zone)
        # 4.  Add network rules for VM (done in base.py itself) to make
        #     it accessible
        # 5.  Verify that VM is accessible
        # 6.  Destroy and expunge the VM
        # 7.  Wait for network gc time interval and check that router is
        #     in stopped state
        """
        # Create VM in account
        virtual_machine = VirtualMachine.create(
            self.userapiclient,
            self.testdata["small"],
            templateid=self.defaultTemplateId,
            accountid=self.account.name,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            networkids=[self.networkid, ] if self.networkid else None,
            zoneid=self.zone.id,
            startvm=True,
            mode=self.zone.networktype
        )

        response = virtual_machine.getState(
            self.userapiclient,
            VirtualMachine.RUNNING)
        self.assertEqual(response[0], PASS, response[1])

        if str(self.zone.networktype).lower() == "advanced":
            response = VerifyRouterState(
                self.apiclient,
                self.account.name,
                self.account.domainid,
                RUNNING
            )
            self.assertTrue(response[0], response[1])

        # Check VM accessibility
        try:
            SshClient(host=virtual_machine.ssh_ip,
                      port=self.testdata["natrule"]["publicport"],
                      user=virtual_machine.username,
                      passwd=virtual_machine.password)
        except Exception as e:
            self.fail("Exception while SSHing to VM: %s" % e)

        virtual_machine.delete(self.apiclient)

        if str(self.zone.networktype).lower() == "advanced":
            # Wait for router to get router in stopped state
            wait_for_cleanup(
                self.apiclient, [
                    "network.gc.interval", "network.gc.wait"])

            response = VerifyRouterState(
                self.apiclient,
                self.account.name,
                self.account.domainid,
                STOPPED,
                retries=10
            )
            self.assertTrue(response[0], response[1])
        return

    @attr(tags=["advanced", "basic"], required_hardware="True")
    def test_06_pt_startvm_false_attach_iso(self):
        """ Positive test for stopped VM test path - T5

        # 1.  Deploy VM in the network with specifying startvm parameter
        #     as False
        # 2.  List VMs and verify that VM is in stopped state
        # 3.  Register an ISO and attach it to the VM
        # 4.  Verify that ISO is attached to the VM
        """

        # Create VM in account
        virtual_machine = VirtualMachine.create(
            self.userapiclient,
            self.testdata["small"],
            templateid=self.defaultTemplateId,
            accountid=self.account.name,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            networkids=[self.networkid, ] if self.networkid else None,
            zoneid=self.zone.id,
            startvm=False,
            mode=self.zone.networktype
        )
        self.cleanup.append(virtual_machine)

        response = virtual_machine.getState(
            self.apiclient,
            VirtualMachine.STOPPED)
        self.assertEqual(response[0], PASS, response[1])

        iso = Iso.create(
            self.userapiclient,
            self.testdata["iso"],
            account=self.account.name,
            domainid=self.account.domainid,
            zoneid=self.zone.id
        )

        iso.download(self.userapiclient)
        virtual_machine.attach_iso(self.userapiclient, iso)

        vms = VirtualMachine.list(
            self.userapiclient,
            id=virtual_machine.id,
            listall=True
        )
        self.assertEqual(
            validateList(vms)[0],
            PASS,
            "List vms should return a valid list"
        )
        vm = vms[0]
        self.assertEqual(
            vm.isoid,
            iso.id,
            "The ISO status should be reflected in list Vm call"
        )
        return

    @attr(tags=["advanced", "basic"], required_hardware="True")
    def test_07_pt_startvm_false_attach_iso_running_vm(self):
        """ Positive test for stopped VM test path - T5 variant

        # 1.  Deploy VM in the network with specifying startvm parameter
        #     as False
        # 2.  List VMs and verify that VM is in stopped state
        # 3.  Start the VM and verify that it is in running state
        # 3.  Register an ISO and attach it to the VM
        # 4.  Verify that ISO is attached to the VM
        """

        # Create VM in account
        virtual_machine = VirtualMachine.create(
            self.userapiclient,
            self.testdata["small"],
            templateid=self.defaultTemplateId,
            accountid=self.account.name,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            networkids=[self.networkid, ] if self.networkid else None,
            zoneid=self.zone.id,
            startvm=False,
            mode=self.zone.networktype
        )
        self.cleanup.append(virtual_machine)

        response = virtual_machine.getState(
            self.apiclient,
            VirtualMachine.STOPPED)
        self.assertEqual(response[0], PASS, response[1])

        virtual_machine.start(self.userapiclient)

        response = virtual_machine.getState(
            self.apiclient,
            VirtualMachine.RUNNING)
        self.assertEqual(response[0], PASS, response[1])

        iso = Iso.create(
            self.userapiclient,
            self.testdata["iso"],
            account=self.account.name,
            domainid=self.account.domainid,
            zoneid=self.zone.id
        )

        iso.download(self.userapiclient)
        virtual_machine.attach_iso(self.userapiclient, iso)

        vms = VirtualMachine.list(
            self.userapiclient,
            id=virtual_machine.id,
            listall=True
        )
        self.assertEqual(
            validateList(vms)[0],
            PASS,
            "List vms should return a valid list"
        )
        vm = vms[0]
        self.assertEqual(
            vm.isoid,
            iso.id,
            "The ISO status should be reflected in list Vm call"
        )
        return

    @attr(tags=["advanced", "basic"], required_hardware="True")
    def test_08_pt_startvm_false_password_enabled_template(self):
        """ Positive test for stopped VM test path - T10

        # 1   Create a password enabled template
        # 2.  Deploy a new VM with password enabled template
        # 3.  Verify that VM is in stopped state
        # 4.  Start the VM, verify that it is in running state
        # 5.  Verify that new password is generated for the VM
        """

        vm_for_template = VirtualMachine.create(
            self.userapiclient,
            self.testdata["small"],
            templateid=self.defaultTemplateId,
            accountid=self.account.name,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            zoneid=self.zone.id,
            mode=self.zone.networktype,
            networkids=[self.networkid, ] if self.networkid else None)

        vm_for_template.password = self.testdata["virtual_machine"]["password"]
        ssh = vm_for_template.get_ssh_client()

        # below steps are required to get the new password from
        # VR(reset password)
        # http://cloudstack.org/dl/cloud-set-guest-password
        # Copy this file to /etc/init.d
        # chmod +x /etc/init.d/cloud-set-guest-password
        # chkconfig --add cloud-set-guest-password
        # similar steps to get SSH key from web so as to make it ssh enabled

        cmds = [
            "cd /etc/init.d;wget http://people.apache.org/~tsp/\
                    cloud-set-guest-password",
            "chmod +x /etc/init.d/cloud-set-guest-password",
            "chkconfig --add cloud-set-guest-password"]
        for c in cmds:
            ssh.execute(c)

        # Stop virtual machine
        vm_for_template.stop(self.userapiclient)

        list_volume = Volume.list(
            self.userapiclient,
            virtualmachineid=vm_for_template.id,
            type='ROOT',
            listall=True)

        if isinstance(list_volume, list):
            self.volume = list_volume[0]
        else:
            raise Exception(
                "Exception: Unable to find root volume for VM: %s" %
                vm_for_template.id)

        self.testdata["template"]["ostype"] = self.testdata["ostype"]
        # Create templates for Edit, Delete & update permissions testcases
        pw_ssh_enabled_template = Template.create(
            self.userapiclient,
            self.testdata["template"],
            self.volume.id,
            account=self.account.name,
            domainid=self.account.domainid
        )
        self.cleanup.append(pw_ssh_enabled_template)
        # Delete the VM - No longer needed
        vm_for_template.delete(self.apiclient)

        # Create VM in account
        virtual_machine = VirtualMachine.create(
            self.userapiclient,
            self.testdata["small"],
            templateid=self.defaultTemplateId,
            accountid=self.account.name,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            zoneid=self.zone.id,
            startvm=False,
            mode=self.zone.networktype,
            networkids=[self.networkid, ] if self.networkid else None
        )
        self.cleanup.append(virtual_machine)

        response = virtual_machine.getState(
            self.apiclient,
            VirtualMachine.STOPPED)
        self.assertEqual(response[0], PASS, response[1])

        virtual_machine.start(self.userapiclient)

        vms = virtual_machine.list(
            self.userapiclient,
            id=virtual_machine.id,
            listall=True)

        self.assertEqual(
            validateList(vms)[0],
            PASS,
            "vms list validation failed"
        )
        self.assertNotEqual(
            str(vms[0].password),
            str(virtual_machine.password),
            "New password should be generated for the VM"
        )
        return