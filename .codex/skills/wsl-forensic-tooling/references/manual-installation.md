# Manual installation review

Use this review for tools that are not installed from the distribution's configured package repositories.

Before requesting authorization, record:

- the capability and why an already installed or `apt`-cataloged tool is unsuitable;
- distribution, architecture, exact product and version;
- official origin URL and the vendor's supported installation method;
- expected download, signature or digest, and how authenticity will be verified;
- destination, privilege level, dependencies, network endpoints, and system changes;
- version command, a harmless validation command, rollback method, and limitations.

Ask for explicit authorization covering the named download source, network access, and installation changes. Pin the reviewed version. Do not use `curl | sh`, execute an unverified download, add a repository, import a signing key, or install into a shared Python environment unless those exact actions were disclosed and authorized.

Store installation records below `Lab/logs/tool-installations/`. A successful installation does not authorize the forensic operation that will use the tool.
