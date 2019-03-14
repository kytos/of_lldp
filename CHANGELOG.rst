#########
Changelog
#########
All notable changes to the of_lldp NApp will be documented in this file.

[UNRELEASED] - Under development
********************************
Added
=====
 - Continuum integration enabled at scrutinizer.

Changed
=======

Deprecated
==========

Removed
=======

Fixed
=====
 - Fixed some linter issues.

Security
========

[0.1.1] - 2018-04-20
********************
Added
=====
- Added REST API section
- Added try statement to notify_uplink method
- Added option to work with VLANs in LLDP exchanges.
- Added methods to send LLDP specific FlowMods.
- Avoid sending PacketOut to the 'OFPP_LOCAL' port.
- Choose port type according to OFP version.
- Make LLDP listen to v0x04 PacketIns too.
- Dispatch 'switch.link' event.
- Assure in_port has a value property.

Changed
=======
- Change Ethernet VLAN to list of VLANs.
