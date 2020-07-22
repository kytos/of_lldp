#########
Changelog
#########
All notable changes to the of_lldp NApp will be documented in this file.

[UNRELEASED] - Under development
********************************
Added
=====
- Added support for automated tests and CI with Travis.
- Added tags decorator to run tests by type and size.
- Added unit tests, increasing coverage to 94%.
- Added persistence module to store LLDP administrative changes.
- Added a REST endpoint to change LLDP polling_time at run time.

Changed
=======

Deprecated
==========

Removed
=======

Fixed
=====

Security
========


[0.1.4] - 2020-03-11
********************

Changed
=======
- Changed README.rst to include some info badges.

Fixed
=====
- Fixed `openapi.yml` file name.
- Fixed Scrutinizer coverage error.


[0.1.3] - 2019-08-30
********************

Added
=====
 - Added REST API to choose interfaces for sending LLDP packets.


[0.1.2] - 2019-03-15
********************

Added
=====
 - Continuous integration enabled at scrutinizer.

Fixed
=====
 - Fixed some linter issues.


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
