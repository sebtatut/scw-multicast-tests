## 1. Installation Usage

```bash
sudo ./install.sh <role> [interface] [vlan_id]
```

### Args

- `role`: `sender` or `receiver`
- `interface` (sender only): Base network interface name (e.g. `eth0`)
- `vlan_id` (sender only): VLAN ID to create a tagged interface (e.g. `100`)

### Examples

- **Sender** (with VLAN interface setup):

  ```bash
  sudo ./install.sh sender eno1 123
  ```

- **Receiver**:

  ```bash
  sudo ./install.sh receiver
  ```

### What It Does

- Installs dependencies: `ffmpeg`, `tshark`, `tsduck`, `smcroute`, etc.
- Builds **SRT v1.5.4** (required by TSDuck)
- Installs **TSDuck 3.33-3139**
- Creates a VLAN interface for the sender (Elastic Metal see https://www.scaleway.com/en/docs/elastic-metal/how-to/use-private-networks/#how-to-configure-the-network-interface-on-your-elastic-metal-server-for-private-networks)
- Configures **smcroute** on the receiver for IGMP support

### Notes

- The script detects a private IP interface automatically (IPv4 ranges: 10.x.x.x, 192.168.x.x, or 172.16–31.x.x).
- Docker interfaces are ignored.


## 2. Sender Test Script Usage

```bash
sudo python3 sender_test.py \
  --interface <net_iface> \
  --ip <private_ip> \
  --pcap <output_file.pcap> \
  --mcast_ip <multicast_ip> \
  --mcast_port <multicast_port> \
  --duration <seconds>
```

### Example

```bash
sudo python3 sender_test.py \
  --interface eno1.1234 \
  --ip 172.16.4.2 \
  --pcap sender_output.pcap \
  --mcast_ip 224.1.1.1 \
  --mcast_port 5000 \
  --duration 300
```

### What It Does

- Streams a 1080p test video and sine wave audio to the given mcast IP/port using ffmpeg
- Captures UDP packets with `tcpdump` for the specified duration
- Saves the capture to the specified `.pcap` file

### Notes

- Run with `sudo`


## 3. Receiver Test Script Usage

```bash
sudo python3 receiver_test.py \
  --interface <net_iface> \
  --ip <local_ip> \
  --mcast_ip <multicast_ip> \
  --mcast_port <port> \
  --pcap <output_file.pcap> \
  --igmp_log <igmp_log.txt> \
  --smcrouted_log <smcrouted_log.txt> \
  --tsp_log <tsp_log.txt> \
  --duration <seconds>
```

### Example

```bash
sudo python3 receiver_test.py \
  --interface enp5s0 \
  --ip 172.16.4.2 \
  --mcast_ip 224.1.1.1 \
  --mcast_port 5000 \
  --pcap receiver_output.pcap \
  --igmp_log igmp_output.txt \
  --smcrouted_log smc_output.txt \
  --tsp_log tsp_report.txt \
  --duration 300
```

### What It Does

- Starts **smcrouted** in debug mode to manage multicast routing
- Captures **IGMP messages** using `tcpdump`
- Dumps **multicast UDP traffic** to a `.pcap` file
- Runs `tsp` to analyze multicast MPEG-TS streams
- All logs are saved to the provided log files

### Notes

- Run with `sudo`


## 4. Setup GRE tunneling

Test encapsulating multicast in unicast

### Sender

#### Steps

##### 1. Verify Reachability

Ensure the receiver endpoint is reachable before creating the tunnel:

```bash
ping -c 4 <receiver_private_ip>
```

#### 2. Create the GRE Tunnel

Create and configure a GRE tunnel interface named `gre1`:

```bash
sudo ip tunnel add <tunnel_iface_name> mode gre local <sender_private_ip> remote <receiver_private_ip> ttl 255
sudo ip link set <tunnel_iface_name> up
sudo ip addr add 10.10.10.1/30 dev <tunnel_iface_name>
```

> Replace <sender_private_ip> and <receiver_private_ip> with your local and remote IPs respectively.

#### 3. Verify Tunnel Connectivity

Ping the remote GRE endpoint (e.g. `10.10.10.2`) to verify tunnel is operational:

```bash
ping -c 4 10.10.10.2
```

#### 4. Inspect Iface State

Check the status and assigned IPs of all ifaces:

```bash
ip -br a
```


### Receiver

#### Steps

##### 1. Verify Reachability

Ensure the sender endpoint is reachable before creating the tunnel:

```bash
ping -c 4 <sender_private_ip>
```

#### 2. Create the GRE Tunnel

Create and configure a GRE tunnel interface named `gre1`:

```bash
sudo ip tunnel add <tunnel_iface_name> mode gre local <receiver_private_ip> remote <sender_private_ip> ttl 255
sudo ip link set <tunnel_iface_name> up
sudo ip addr add 10.10.10.2/30 dev <tunnel_iface_name>
```

> Replace <sender_private_ip> and <receiver_private_ip> with your local and remote IPs respectively.

#### 3. Verify Tunnel Connectivity

Ping the remote GRE endpoint (e.g. `10.10.10.1`) to verify tunnel is operational:

```bash
ping -c 4 10.10.10.1
```

#### 4. Inspect Iface State

Check the status and assigned IPs of all ifaces:

```bash
ip -br a
```
