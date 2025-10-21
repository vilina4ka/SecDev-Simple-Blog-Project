# DFD — Simple Blog

```mermaid
flowchart TD
  User[User] -->|F1: Login / Auth| Edge[Edge Server]

  User -->|F2: Create Post| Edge
  User -->|F3: View Public Feed| Edge
  User -->|F3a: Filter by Tag/Status| Edge
  User -->|F3b: View Own Posts| Edge
  User -->|F4: Edit Own Post| Edge
  User -->|F5: Delete Own Post| Edge

  subgraph TrustBoundary1["Client / Edge"]
    User
    Edge
  end

  subgraph TrustBoundary2["Core / DB"]
    Core[Core Logic]
    DB[(Database)]
  end

  Edge -->|F6: Validate & Process Requests| Core
  Core -->|F7: Read/Write Posts| DB

  subgraph Core_Processing["Core Internal"]
    Core_Process[Internal Processing]
  end

  Core --> Core_Process
