"""NApp responsible to discover new switches and hosts."""
import struct

from kytos.core import KytosEvent, KytosNApp, log
from kytos.core.helpers import listen_to

from pyof.foundation.basic_types import DPID, UBInt16, UBInt32
from pyof.foundation.network_types import LLDP, Ethernet, EtherType
from pyof.v0x01.common.action import ActionOutput as AO10
from pyof.v0x01.common.phy_port import Port as Port10
from pyof.v0x01.controller2switch.flow_mod import FlowMod as FM10
from pyof.v0x01.controller2switch.flow_mod import FlowModCommand as FMC
from pyof.v0x01.controller2switch.packet_out import PacketOut as PO10
from pyof.v0x04.common.action import ActionOutput as AO13
from pyof.v0x04.common.flow_instructions import InstructionApplyAction
from pyof.v0x04.common.flow_match import OxmOfbMatchField, OxmTLV
from pyof.v0x04.common.port import PortNo as Port13
from pyof.v0x04.controller2switch.flow_mod import FlowMod as FM13
from pyof.v0x04.controller2switch.packet_out import PacketOut as PO13

from napps.kytos.of_lldp import constants, settings


class Main(KytosNApp):
    """Main OF_LLDP NApp Class."""

    def setup(self):
        """Make this NApp run in a loop."""
        self.execute_as_loop(settings.POLLING_TIME)

    def execute(self):
        """Send LLDP Packets every 'POLLING_TIME' seconds to all switches."""
        switches = list(self.controller.switches.values())
        for switch in switches:
            try:
                of_version = switch.connection.protocol.version
            except AttributeError:
                of_version = None

            if not switch.is_connected():
                continue

            if of_version == 0x01:
                port_type = UBInt16
                local_port = Port10.OFPP_LOCAL
            elif of_version == 0x04:
                port_type = UBInt32
                local_port = Port13.OFPP_LOCAL
            else:
                # skip the current switch with unsupported OF version
                continue

            interfaces = list(switch.interfaces.values())
            for interface in interfaces:

                # Avoid the interface that connects to the controller.
                if interface.port_number == local_port:
                    continue

                lldp = LLDP()
                lldp.chassis_id.sub_value = DPID(switch.dpid)
                lldp.port_id.sub_value = port_type(interface.port_number)

                ethernet = Ethernet()
                ethernet.ether_type = EtherType.LLDP
                ethernet.source = interface.address
                ethernet.destination = constants.LLDP_MULTICAST_MAC
                ethernet.data = lldp.pack()

                packet_out = self._build_lldp_packet_out(of_version,
                                                         interface.port_number,
                                                         ethernet.pack())

                if packet_out is not None:
                    name = 'kytos/of_lldp.messages.out.ofpt_packet_out'
                    content = {'destination': switch.connection,
                               'message': packet_out}
                    event_out = KytosEvent(name=name, content=content)
                    self.controller.buffers.msg_out.put(event_out)

                    log.debug("Sending a LLDP PacketOut to the switch %s",
                              switch.dpid)

                    msg = '\n'
                    msg += 'Switch: %s (%s)\n'
                    msg += '  Interfaces: %s\n'
                    msg += '  -- LLDP PacketOut --\n'
                    msg += '  Ethernet: eth_type (%s) | src (%s) | dst (%s)\n'
                    msg += '    LLDP: Switch (%s) | port (%s)'

                    log.debug(msg, switch.connection.address, switch.dpid,
                              switch.interfaces, ethernet.ether_type,
                              ethernet.source, ethernet.destination,
                              switch.dpid, interface.port_number)

    @listen_to('kytos/core.switch.new')
    def install_lldp_flow(self, event):
        """Install a flow to send LLDP packets to the controller.

        The proactive flow is installed whenever a switch connects.

        Args:
            event (:class:`~kytos.core.events.KytosEvent`):
                Event with new switch information.

        """
        try:
            of_version = event.content['switch'].connection.protocol.version
        except AttributeError:
            of_version = None

        flow_mod = self._build_lldp_flow_mod(of_version)

        if flow_mod:
            name = 'kytos/of_lldp.messages.out.ofpt_flow_mod'
            content = {'destination': event.content['switch'].connection,
                       'message': flow_mod}

            event_out = KytosEvent(name=name, content=content)
            self.controller.buffers.msg_out.put(event_out)

    @listen_to('kytos/of_core.v0x0[14].messages.in.ofpt_packet_in')
    def notify_uplink_detected(self, event):
        """Dispatch two KytosEvents to notify identified NNI interfaces.

        Args:
            event (:class:`~kytos.core.events.KytosEvent`):
                Event with an LLDP packet as data.

        """
        ethernet = self._unpack_non_empty(Ethernet, event.message.data)
        if ethernet.ether_type == EtherType.LLDP:
            try:
                lldp = self._unpack_non_empty(LLDP, ethernet.data)
                dpid = self._unpack_non_empty(DPID, lldp.chassis_id.sub_value)
            except struct.error:
                #: If we have a LLDP packet but we cannot unpack it, or the
                #: unpacked packet does not contain the dpid attribute, then
                #: we are dealing with a LLDP generated by someone else. Thus
                #: this packet is not useful for us and we may just ignore it.
                return

            switch_a = event.source.switch
            port_a = event.message.in_port

            switch_b = self.controller.get_switch_by_dpid(dpid.value)
            of_version = switch_b.connection.protocol.version
            port_type = UBInt16 if of_version == 0x01 else UBInt32
            port_b = self._unpack_non_empty(port_type, lldp.port_id.sub_value)

            # Return if any of the needed information are not available
            if not (switch_a and port_a and switch_b and port_b):
                return

            name = 'kytos/of_lldp.interface.is.nni'
            content = {'switch': switch_a.id, 'port': port_a}
            event_out = KytosEvent(name=name, content=content)
            self.controller.buffers.app.put(event_out)

            content = {'switch': switch_b.id, 'port': port_b}
            event_out = KytosEvent(name=name, content=content)
            self.controller.buffers.app.put(event_out)

    def shutdown(self):
        """End of the application."""
        log.debug('Shutting down...')

    @staticmethod
    def _build_lldp_packet_out(version, port_number, data):
        """Build a LLDP PacketOut message.

        Args:
            version (int): OpenFlow version
            port_number (int): Switch port number where the packet must be
                forwarded to.
            data (bytes): Binary data to be sent through the port.

        Returns:
            PacketOut message for the specific given OpenFlow version, if it
                is supported.
            None if the OpenFlow version is not supported.

        """
        if version == 0x01:
            action_output_class = AO10
            packet_out_class = PO10
        elif version == 0x04:
            action_output_class = AO13
            packet_out_class = PO13
        else:
            log.info('Openflow version %s is not yet supported.', version)
            return None

        output_action = action_output_class()
        output_action.port = port_number

        packet_out = packet_out_class()
        packet_out.data = data
        packet_out.actions.append(output_action)

        return packet_out

    @staticmethod
    def _build_lldp_flow_mod(version):
        """Build a FlodMod message to send LLDP to the controller.

        Args:
            version (int): OpenFlow version.

        Returns:
            FlowMod message for the specific given OpenFlow version, if it is
                supported.
            None if the OpenFlow version is not supported.

        """
        if version == 0x01:
            flow_mod = FM10()
            flow_mod.command = FMC.OFPFC_ADD
            flow_mod.priority = settings.FLOW_PRIORITY
            flow_mod.match.dl_type = EtherType.LLDP
            flow_mod.actions.append(AO10(port=Port10.OFPP_CONTROLLER))

        elif version == 0x04:
            flow_mod = FM13()
            flow_mod.command = FMC.OFPFC_ADD
            flow_mod.priority = settings.FLOW_PRIORITY

            match_lldp = OxmTLV()
            match_lldp.oxm_field = OxmOfbMatchField.OFPXMT_OFB_ETH_TYPE
            match_lldp.oxm_value = EtherType.LLDP.to_bytes(2, 'big')
            flow_mod.match.oxm_match_fields.append(match_lldp)

            instruction = InstructionApplyAction()
            instruction.actions.append(AO13(port=Port13.OFPP_CONTROLLER))
            flow_mod.instructions.append(instruction)

        else:
            flow_mod = None

        return flow_mod

    @staticmethod
    def _unpack_non_empty(desired_class, data):
        """Unpack data using an instance of desired_class.

        Args:
            desired_class (class): The class to be used to unpack data.
            data (bytes): bytes to be unpacked.

        Return:
            An instance of desired_class class with data unpacked into it.

        Raises:
            UnpackException if the unpack could not be performed.

        """
        obj = desired_class()

        if hasattr(data, 'value'):
            data = data.value

        obj.unpack(data)

        return obj
