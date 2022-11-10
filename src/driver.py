#!/usr/bin/python
from __future__ import annotations

from typing import TYPE_CHECKING

from cloudshell.cli.service.cli import CLI
from cloudshell.cli.service.session_pool_manager import SessionPoolManager
from cloudshell.shell.core.driver_utils import GlobalLock
from cloudshell.shell.core.orchestration_save_restore import OrchestrationSaveRestore
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.flows.command.basic_flow import RunCommandFlow
from cloudshell.shell.flows.connectivity.parse_request_service import (
    ParseConnectivityRequestService,
)
from cloudshell.shell.flows.state.basic_flow import StateFlow
from cloudshell.shell.standards.networking.autoload_model import NetworkingResourceModel
from cloudshell.shell.standards.networking.driver_interface import (
    NetworkingResourceDriverInterface,
)
from cloudshell.shell.standards.networking.resource_config import (
    NetworkingResourceConfig,
)
from cloudshell.snmp.snmp_configurator import EnableDisableSnmpConfigurator

from cloudshell.networking.arista.cli.arista_cli_configurator import (
    AristaCLIConfigurator,
)
from cloudshell.networking.arista.flows.arista_autoload_flow import AristaAutoloadFlow
from cloudshell.networking.arista.flows.arista_configuration_flow import (
    AristaConfigurationFlow,
)
from cloudshell.networking.arista.flows.arista_connectivity_flow import (
    AristaConnectivityFlow,
)
from cloudshell.networking.arista.flows.arista_load_firmware_flow import (
    AristaLoadFirmwareFlow,
)
from cloudshell.networking.arista.flows.enable_disable_snmp import (
    AristaEnableDisableSNMPFlow,
)

if TYPE_CHECKING:
    from cloudshell.shell.core.driver_context import (
        AutoLoadCommandContext,
        AutoLoadDetails,
        InitCommandContext,
        ResourceCommandContext,
    )


class AristaEosSwitchShell2GDriver(
    ResourceDriverInterface, NetworkingResourceDriverInterface
):
    SUPPORTED_OS = ["Arista", "EOS"]
    SHELL_NAME = "AristaEosSwitchShell2G"

    def __init__(self):
        super().__init__()
        self._cli = None

    def initialize(self, context: InitCommandContext):
        """Initialize method."""
        resource_config = NetworkingResourceConfig.from_context(
            self.SHELL_NAME, context, None, self.SUPPORTED_OS
        )

        session_pool_size = int(resource_config.sessions_concurrency_limit)
        self._cli = CLI(
            SessionPoolManager(max_pool_size=session_pool_size, pool_timeout=100)
        )
        return "Finished initializing"

    @GlobalLock.lock
    def get_inventory(self, context: AutoLoadCommandContext) -> AutoLoadDetails:
        """Return device structure with all standard attributes."""
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME, context, api, self.SUPPORTED_OS
            )

            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            enable_disable_snmp_flow = AristaEnableDisableSNMPFlow(
                cli_configurator, logger, resource_config.vrf_management_name
            )
            snmp_configurator = EnableDisableSnmpConfigurator(
                enable_disable_snmp_flow, resource_config, logger
            )

            resource_model = NetworkingResourceModel.from_resource_config(
                resource_config
            )

            autoload_operations = AristaAutoloadFlow(snmp_configurator, logger)
            logger.info("Autoload started")
            response = autoload_operations.discover(self.SUPPORTED_OS, resource_model)
            logger.info("Autoload completed")
            return response

    def run_custom_command(
        self, context: ResourceCommandContext, custom_command: str
    ) -> str:
        """Send custom command."""
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )

            send_command_flow = RunCommandFlow(logger, cli_configurator)
            response = send_command_flow.run_custom_command(custom_command)
            return response

    def run_custom_config_command(
        self, context: ResourceCommandContext, custom_command: str
    ) -> str:
        """Send custom command in configuration mode."""
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )

            send_command_flow = RunCommandFlow(logger, cli_configurator)
            response = send_command_flow.run_custom_config_command(custom_command)
            return response

    def ApplyConnectivityChanges(
        self, context: ResourceCommandContext, request: str
    ) -> str:
        """Create vlan and add or remove it to/from network interface."""
        with LoggingSessionContext(context) as logger:
            logger.info("Apply Connectivity command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            connectivity_request_service = ParseConnectivityRequestService(
                is_vlan_range_supported=True, is_multi_vlan_supported=True
            )
            flow = AristaConnectivityFlow(
                connectivity_request_service, logger, resource_config, cli_configurator
            )
            result = flow.apply_connectivity(request)
            logger.info(f"Apply connectivity command finished with response {result}")
            return result

    def save(
        self,
        context: ResourceCommandContext,
        folder_path: str,
        configuration_type: str,
        vrf_management_name: str,
    ) -> str:
        """Save selected file to the provided destination.

        :param context: ResourceCommandContext object with
            all Resource Attributes inside
        :param configuration_type: source file, which will be saved
        :param folder_path: destination path where file will be saved
        :param vrf_management_name: VRF management Name
        :return: saved configuration file name.
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Apply Connectivity command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            flow = AristaConfigurationFlow(logger, resource_config, cli_configurator)
            result = flow.save(folder_path, configuration_type, vrf_management_name)
            logger.info("Save command completed")
            return result

    @GlobalLock.lock
    def restore(
        self,
        context: ResourceCommandContext,
        path: str,
        configuration_type: str,
        restore_method: str,
        vrf_management_name: str,
    ) -> None:
        """Restore selected file to the provided destination.

        :param ResourceCommandContext context: ResourceCommandContext object
            with all Resource Attributes inside
        :param path: source config file
        :param configuration_type: running or startup configs
        :param restore_method: append or override methods
        :param vrf_management_name: VRF management Name
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Apply Connectivity command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            if not configuration_type:
                configuration_type = "running"

            if not restore_method:
                restore_method = "override"

            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            flow = AristaConfigurationFlow(logger, resource_config, cli_configurator)
            flow.restore(path, configuration_type, restore_method, vrf_management_name)
            logger.info("Restore command completed")

    def orchestration_save(
        self, context: ResourceCommandContext, mode: str, custom_params: str
    ) -> str:
        """Orchestration save.

        :param context: ResourceCommandContext object with
            all Resource Attributes inside
        :param mode: mode
        :param custom_params: json with custom save parameters
        :return response: response json
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Orchestration save command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )

            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            flow = AristaConfigurationFlow(logger, resource_config, cli_configurator)
            result = flow.orchestration_save(mode, custom_params)
            response_json = OrchestrationSaveRestore(
                logger, resource_config.name
            ).prepare_orchestration_save_result(result)
            logger.info("Orchestration save command completed")
            return response_json

    def orchestration_restore(
        self,
        context: ResourceCommandContext,
        saved_artifact_info: str,
        custom_params: str,
    ) -> None:
        """Restores a saved artifact previously saved by this Shell driver.

        :param ResourceCommandContext context: ResourceCommandContext object
            with all Resource Attributes inside
        :param saved_artifact_info: OrchestrationSavedArtifactInfo json
        :param custom_params: json with custom restore parameters
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Orchestration restore command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )

            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            flow = AristaConfigurationFlow(logger, resource_config, cli_configurator)
            restore_params = OrchestrationSaveRestore(
                logger, resource_config.name
            ).parse_orchestration_save_result(saved_artifact_info)
            flow.restore(**restore_params)
            logger.info("Orchestration restore command completed")

    @GlobalLock.lock
    def load_firmware(
        self, context: ResourceCommandContext, path: str, vrf_management_name: str
    ) -> None:
        """Upload and updates firmware on the resource.

        :param ResourceCommandContext context: ResourceCommandContext object
            with all Resource Attributes inside
        :param path: full path to firmware file, i.e. tftp://10.10.10.1/firmware.tar
        :param vrf_management_name: VRF management Name
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Load firmware command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )
            flow = AristaLoadFirmwareFlow(logger, resource_config, cli_configurator)
            flow.load_firmware(path, vrf_management_name)
            logger.info("Finish Load Firmware")

    def health_check(self, context: ResourceCommandContext) -> str:
        """Performs device health check.

        :param ResourceCommandContext context: ResourceCommandContext object
            with all Resource Attributes inside
        :return: Success or Error message
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Load firmware command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )

            flow = StateFlow(logger, resource_config, cli_configurator, api)
            result = flow.health_check()
            logger.info(f"Health Check command ended with result: {result}")
            return result

    def cleanup(self):
        pass

    def shutdown(self, context: ResourceCommandContext) -> str:
        """Shutdown device.

        :param ResourceCommandContext context: ResourceCommandContext object
            with all Resource Attributes inside
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Load firmware command started")
            api = CloudShellSessionContext(context).get_api()
            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = AristaCLIConfigurator(
                resource_config, api, logger, self._cli
            )

            flow = StateFlow(logger, resource_config, cli_configurator, api)
            return flow.shutdown()
