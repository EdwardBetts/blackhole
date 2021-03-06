package com.cloud.hypervisor.kvm.resource;

import java.util.HashMap;
import java.util.Map;

import com.cloud.hypervisor.Hypervisor.HypervisorType;

import org.libvirt.Connect;
import org.libvirt.LibvirtException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LibvirtConnection {
  private static final Logger LOGGER = LoggerFactory.getLogger(LibvirtConnection.class);

  private static Map<String, Connect> connections = new HashMap<String, Connect>();

  private static Connect connection;
  private static String hypervisorUri;

  public static Connect getConnection() throws LibvirtException {
    return getConnection(hypervisorUri);
  }

  public static Connect getConnection(String hypervisorUri) throws LibvirtException {
    LOGGER.debug("Looking for libvirtd connection at: " + hypervisorUri);
    Connect conn = connections.get(hypervisorUri);

    if (conn == null) {
      LOGGER.info("No existing libvirtd connection found. Opening a new one");
      conn = new Connect(hypervisorUri, false);
      LOGGER.debug("Successfully connected to libvirt at: " + hypervisorUri);
      connections.put(hypervisorUri, conn);
    } else {
      try {
        conn.getVersion();
      } catch (final LibvirtException e) {
        LOGGER.error("Connection with libvirtd is broken: " + e.getMessage());
        LOGGER.debug("Opening a new libvirtd connection to: " + hypervisorUri);
        conn = new Connect(hypervisorUri, false);
        connections.put(hypervisorUri, conn);
      }
    }

    return conn;
  }

  public static Connect getConnectionByVmName(String vmName) throws LibvirtException {
    final HypervisorType[] hypervisors = new HypervisorType[] { HypervisorType.KVM };

    for (final HypervisorType hypervisor : hypervisors) {
      try {
        final Connect conn = LibvirtConnection.getConnectionByType(hypervisor.toString());
        if (conn.domainLookupByName(vmName) != null) {
          return conn;
        }
      } catch (final Exception e) {
        LOGGER.debug(
            "Can not find " + hypervisor.toString() + " connection for Instance: " + vmName + ", continuing.");
      }
    }

    LOGGER.warn("Can not find a connection for Instance " + vmName + ". Assuming the default connection.");
    // return the default connection
    return getConnection();
  }

  public static Connect getConnectionByType(String hypervisorType) throws LibvirtException {
    return getConnection(getHypervisorUri(hypervisorType));
  }

  static void initialize(String hypervisorUri) {
    LibvirtConnection.hypervisorUri = hypervisorUri;
  }

  static String getHypervisorUri(String hypervisorType) {
    return "qemu:///system";
  }
}