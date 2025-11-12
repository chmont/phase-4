# Introduction
The goal of this internship project is to gain hands-on experience with modern monitoring and observability practices using Prometheus and Grafana. This project is divided into phases that build progressively. The main objectives are to learn how metrics are collected, stored, and queried, and how they can be visualized in Grafana dashboards to improve visibility into system performance.
The motivation behind this project is to understand how DevOps teams use monitoring tools to detect issues early, automate monitoring, and ensure reliable operations.


## PHASE 0 Environment Setup and Baseline
Machine specs:
- OS: Windows 11
- Memory: 32gb
- CPU: Intel Core i7-8850H CPU @2.60Ghz (6 cores, 12 threads)

Tools:
- Prometheus v3.6.0
- Grafana (grafana-enterprise v12.2.0)
- Docker v28.4.0
- Windows PowerShell 7
- Mimir 

## PHASE 1 - Prometheus & Grafana Basics

### Task 
- Install Prometheus locally
- Install Grafana locally
- Add Windows Exporter and Blackbox Exporter

### Concepts Explained

#### Grafana:
Grafana is a visualation tool that queires from a data source like Promtheus and turns tht raw time series metrics into dashboards. In this phase of the project I used it to visualze CPU and memory usage from windows exporter, and HTTP probe results from Blackbox Exporter. 

#### Prometheus
Prometheus is a monitoring and alerting system that uses a pull base model. It pulls and scrapes metrics from targets at a fixed interval and stores them in a time series database (TSDB). Metrics are identified by labels and names. 

- Metric name is an aspect of a system or service that you're measuring.
- Lables are key value pairs attached to metrics.

Labels give extra content so the same metric name can represent many different time series and make filtering and grouping possible. Promtheus automatically attaches some of these labels to tell you which targets these time series came from (Also caled target labels).

#### Blackbox Exporter
Blackbox exporter allows Prometheus to check external endpoints like websites, APIs, and TCP ports. It returns metrics such as:
- probe_success (1 = up, 0 = down)
- probe_duration_seconds (latency in seconds)

This makes it useful for uptime monitoring and response time tracking.

Examples:

- Blackbox Exporter can monitor whether a public website like https://google.com is reachable and how long it takes to respond, helping alert the team if the site goes down so necessary actions can be taken.

- Windows exporter can track CPU, memory, or disk usage on a windows server, so the team can be alerted if reources run too high and risk slowing down applications. 
address-cleanse.gaine.com
#### PromQL (Prometheus Query Langauge)


**CPU Usge %:** 
- Calculates non-idle CPU usage across all cores.
- Used time series as the visualzation because we are viewing cpu usage during that current time.
```bash 
100 * (1 - (rate(windows_cpu_time_total{mode="idle"}[5m])))
```

**Memory Usage:**

```bash
100 * (1 - windows_memory_available_bytes / windows_memory_physical_total_bytes)
```
- Calculates the total memoruy currently being used
- Used Gauge because it measures metrics that either go up or down . 

**Disk Usage**
```bash
100 * (1- (windows_logical_disk_free_bytes{volume = "C:"} /windows_logical_disk_size_bytes{volume = "C:"}))
```
- Calculates the percentage of disk space used on the C: drive by
comparing the available free space to total size of disk.


**Probing:**
- Checks how long it takes blackbox exporter in seconds to probe google.com
```bash
probe_duration_seconds{instance="https://google.com"}
```

### Alerting
Prometheus alerting works by defining alerting rules in PromQl, and when conditions are met it sends to the Alertmanager, which handles notifications.

## Phase 2 - Containerize with Docker
Running Grafana and Prometheus as containers
#### Docker compose:
Docker Compose is not a container—it’s a tool that: 

- Reads your docker-compose.yml configuration file.
- Starts multiple containers (called services).
- Connects them together on a shared virtual network.
- Manages their lifecycle as one project.

#### Docker view logs
Running the Stack

Run your monitoring stack using:

docker compose up -d

Explanation:

up → Starts or rebuilds services.
-d → Runs containers in detached (background) mode.

To stop the stack:

docker compose down

To stop and remove volumes:

docker compose down --volumes

Viewing Logs

To view all logs:

docker compose logs

To view logs for a single service:

docker compose logs prometheus

To follow logs live:

docker compose logs -f grafana

#### How to run alert Manager
This is assuming you have preomtheus running as well as blackbox exporter and windows exporter. 

1. In order to run alertmanger for prometheus you must download the zip file for alertmanager on https://prometheus.io/download/.

2. Unzip the folder and navigate the folder until you see **`alertmanager.exe`** and **`alertmanager.yml`**

3. Configure **`alertmanager.yml`** to route your alerts to the service of your choice. (i.e email, slack, teams, discord, phone numer etc.)
    - look at alertmanager.yml in prometheus folder in this repo folder as an example.   

4. After you configure **``alertmanager.yml``** navigate to your prometheus folder on your local machine and create a file called **`alerts.yml`** 

5. Configure **``alerts.yml``** to setup a PromQL rule on what you want to be notified on. 
    - See alerts.yml in prometheus folder in this repo as an example.

6. Lastly configure your **``prometheus.yml``** to add **``alerts.yml``** under the rules config. 
    - See prometheus.yml in prometheus folder in this repo as an example.

7. Navigate back to where ever your alertsmanger folder is and run the executable **``alertmanager.exe``** in your terminal with these flags
    ```bash
    .\alertmanager.exe --config.file=alertmanager.yml --web.listen-address=:9093
    ```
    - you don't need to run the process with these flags this is just an explict way.
8. Navigate to where blackbox exporter folder is and run the executable **``blackbox_exporter``**
    ```bash
    .\blackbox_exporter.exe
    ```
9. Navigate back to where your prometheus folder is and run the executable **``prometheus.exe``** in your terminal with these commands
    ```bash
    .\prometheus.exe --config.file=prometheus.yml --web.listen-address=:9090
    ```
    - you don't need to run the process with these flags this is just an explict way.


# Getting Started
TODO: Guide users through getting your code up and running on their own system. In this section you can talk about:
1.	Installation process
2.	Software dependencies
3.	Latest releases
4.	API references

# Build and Test
TODO: Describe and show how to build your code and run the tests. 

# Contribute
TODO: Explain how other users and developers can contribute to make your code better. 

If you want to learn more about creating good readme files then refer the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)
- new line
