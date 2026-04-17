# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in **Orbiteus**, please report it **privately** — do **not** open a public GitHub issue for undisclosed vulnerabilities.

**Preferred channel**

- Use GitHub **[Report a vulnerability](https://github.com/orbiteus/orbiteus/security)** for this repository (private vulnerability reporting).  
  Repository owners: enable it under **Settings → Code security and analysis → Private vulnerability reporting** if it is not already on, so researchers can submit reports safely.

**If that workflow is unavailable**

- Contact the **[Orbiteus](https://github.com/orbiteus)** organization or repository maintainers via GitHub to obtain a direct, non-public channel (e.g. a monitored security email).

## What to include

- Description of the vulnerability  
- Steps to reproduce (or a minimal proof of concept)  
- Affected components (e.g. `backend/`, `admin-ui/`, specific module)  
- Potential impact and your severity estimate  
- Suggested fix (if you have one)

## What to expect

| Step | Timeline |
|------|----------|
| Acknowledgment of your report | Within **48 hours** |
| Initial assessment and severity classification | Within **7 days** |
| Fix timeline communicated to you | Within **14 days** |
| Patch released | Depends on severity (**critical:** as fast as practical; **high:** target within **30 days**; **medium/low:** next reasonable release) |

We will keep you informed throughout the process and credit you in release notes **unless you prefer to remain anonymous**.

## Scope

**In scope** for coordinated disclosure with this project:

- Authentication and session management weaknesses (JWT, cookies, logout, session fixation)  
- Authorization and **RBAC** privilege escalation  
- **Cross-tenant** data leakage or tenant isolation bypasses  
- Injection vulnerabilities (**SQL**, **XSS**, command injection, unsafe deserialization)  
- Cryptographic or **secret-handling** weaknesses (tokens, passwords, signing keys)  
- Sensitive data exposure (logs, errors, API responses, OpenAPI exposure in prod)  
- **CSRF**, **SSRF**, or other request forgery affecting the app or API  
- **Dependency** issues with a **demonstrated** exploit path against supported versions of Orbiteus  

**Out of scope**

- Reports from automated scanners **without** a demonstrated exploit path  
- Denial of service via brute-force volume **unless** there is meaningful amplification or a trivial cost asymmetry  
- Social engineering  
- Issues in **third-party** services, hosting, or infrastructure **not** maintained in this repository  
- Deployments running **unsupported**, **EOL**, or **heavily modified** forks without a clear path to upstream  

## Safe harbor

We treat security research conducted in **good faith** as authorized. We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations, data destruction, and service disruption  
- Report vulnerabilities through the **private** channels above  
- Allow **reasonable time** for a fix before public disclosure  

## Supported versions

Security fixes are applied to the **latest maintained release** on the default branch (`main`) and tagged releases as appropriate. **Older tags** are not guaranteed to receive backports unless maintainers deem a vulnerability **critical** and backporting is practical.

## Supply chain and repository hygiene

This monorepo is primarily **consumed from source** (`backend/` Python, `admin-ui/` Next.js). There is **no** published `@orbiteus/*` npm package from this repository at this time, and **GitHub Actions / npm provenance / production publish gates** are not yet documented here as mandatory controls.

**Today:** verify integrity by cloning from **[github.com/orbiteus/orbiteus](https://github.com/orbiteus/orbiteus)**, reviewing `CHANGELOG.md`, and pinning to **verified tags** for production.

**When** CI/CD, container signing, or package publishing are formalized, this section will be updated with concrete verification steps.

There is **no** `CODEOWNERS` file yet; sensitive path review relies on maintainer PR practice until one is added.

## Security-related resources

- Architecture and security model: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (multi-tenancy, RBAC, phases)  
- Auth module (API surface, tokens): [`backend/modules/auth/`](backend/modules/auth/)  
- Core security helpers (middleware, tokens, RBAC primitives): [`backend/orbiteus_core/security/`](backend/orbiteus_core/security/)  

For coordinated disclosure status and advisories, use the repository **Security** tab on GitHub.
