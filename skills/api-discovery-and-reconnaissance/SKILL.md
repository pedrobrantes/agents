# API Discovery & Reconnaissance (CLI/TUI)

## Overview
Advanced mapping, interception, and fuzzing of documented and undocumented (Shadow) APIs strictly using Command Line Interfaces (CLI) and Terminal User Interfaces (TUI). The approach emphasizes a data-driven, layered reconnaissance pipeline: from passive OSINT gathering to active directory brute-forcing and real-time traffic manipulation.

## Core Competencies

### 1. Surface Mapping & OSINT (Passive)
Gathering external infrastructure data without triggering target firewalls.
* **Subfinder:** Rapid Go-based subdomain discovery querying public databases (e.g., SSL certificate logs).
* **Waybackurls / Gau (GetAllUrls):** Extracting historical URL paths from web archives to uncover legacy endpoints (v1, v2) that lack modern WAF protections.
* **LinkFinder:** Python-based static analysis of frontend JavaScript files to extract hardcoded API routes and parameters.

### 2. Dynamic Interception & Traffic Analysis
Acting as a Man-in-the-Middle (MitM) to inspect, capture, and modify real-time application traffic.
* **mitmproxy:** Terminal-based interactive HTTPS proxy. Essential for mobile app (Android) reverse engineering, bypassing certificate pinning, and exporting raw requests.
* **tshark:** CLI version of Wireshark for deep packet inspection on non-HTTP protocols (WebSockets, MQTT, gRPC).

### 3. Active Discovery & Fuzzing
Brute-forcing directories, headers, and parameters to uncover hidden endpoints and bypass access controls.
* **ffuf (Fuzz Faster U Fool):** High-speed Go fuzzer. Utilizes auto-calibration (`-ac`) to intelligently filter out dynamic "Catch-All" false positives.
* **Kiterunner (kr):** API-specific fuzzer that understands RESTful architecture (GET, POST, PUT, DELETE) and deeply maps routes using optimized `.kite` datasets.
* **Nuclei:** Template-based vulnerability scanner highly effective at locating exposed `swagger.json`, `openapi.yaml`, and misconfigured GraphQL endpoints.

### 4. Dataset Curation (Wordlists)
Selecting and managing the correct payloads for specific fuzzing targets.
* **SecLists:** The foundational dataset. Used for generic path discovery (`raft-large-directories.txt`) and subdomain mapping.
* **Assetnote:** Continuously updated, context-aware wordlists scraped from modern web applications. Ideal for Kiterunner.
* **CEWL:** Custom wordlist generator that scrapes the target's website to build a dictionary based on business-specific terminology.

### 5. Interaction & Data Mining
Testing endpoints and structuring JSON responses directly in the terminal.
* **cURL:** The robust, ubiquitous standard for raw HTTP request execution and TLS impersonation testing.
* **HTTPie (`http`):** Modern, developer-friendly CLI HTTP client with native JSON support and syntax highlighting.
* **jq:** The command-line JSON processor. Crucial for slicing, filtering, and structuring massive API responses into readable data pipelines.

---
*Maintained for terminal-centric cli/tui workflows
