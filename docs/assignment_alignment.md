# Assignment Alignment

This system covers the project brief by including customer information, billing rates, water usage records, generated bills, payment history, secure login, public services, registered customer portals, administrator management pages, branch manager analytics, distributed database reporting across PostgreSQL and MySQL, notification records, leak reporting and service requests.

The system implements a heterogeneous distributed database design where PostgreSQL works as the primary operational database and MySQL works as the secondary synchronized database for selected copies/fragments of WASCO records. The report page verifies record distribution by comparing customer, usage, bill and payment counts across both DBMS platforms.

The payment area is integration-ready with an online gateway flow, callback endpoint and local recording process. Real production payments require merchant credentials from the selected payment provider.
