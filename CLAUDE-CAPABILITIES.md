# Claude's Capabilities & Limitations for Statute App

**Last Updated:** October 5, 2026  
**Claude Model:** Claude Haiku 4.5  
**Knowledge Cutoff:** January 2025  

---

## ✅ What I CAN Do

### Code & Development
- ✅ Write Python, JavaScript, HTML, CSS, Bash
- ✅ Create and modify files in the repository
- ✅ Run tests locally (bash, Python)
- ✅ Write comprehensive documentation
- ✅ Create git commits locally
- ✅ Review code and suggest improvements
- ✅ Debug issues and troubleshoot problems
- ✅ Design APIs and system architecture
- ✅ Write SQL queries and database schemas

### GitHub (via MCP Connector)
- ✅ **Push files to main branch** (with OAuth credentials)
- ✅ Create/update files remotely
- ✅ Create pull requests
- ✅ Read repository contents
- ✅ List commits and branches
- ✅ Search code

### Documentation
- ✅ Write deployment guides
- ✅ Create project documentation
- ✅ Document APIs and architecture
- ✅ Write test plans
- ✅ Create checklists and roadmaps
- ✅ Draft emails and messages

### Analysis & Research
- ✅ Research APIs and external services
- ✅ Compare different approaches
- ✅ Analyze code structure
- ✅ Plan feature implementations
- ✅ Review test coverage

---

## ❌ What I CANNOT Do

### Local GitHub Operations
- ❌ **Run `git push origin main` locally** (no local git credentials in this environment)
  - **Workaround:** Use GitHub MCP connector to push files via API
  - **or:** Owner runs `git push` from their machine with local credentials

### Network Access
- ❌ Make HTTP requests to external APIs from this environment
  - Tests show 403 Forbidden (network policy blocks outbound)
  - **Workaround:** APIs work when deployed to GitHub Pages (no restriction there)

### Live Testing
- ❌ Test that live APIs return real data
  - Can only test locally, which blocks API calls
  - **Workaround:** Owner verifies after deployment to GitHub Pages

### Authentication
- ❌ Handle user accounts or secrets locally
  - Can use OAuth secrets via MCP connectors
  - Cannot store credentials in code

### Real-Time Operations
- ❌ Monitor GitHub Actions workflows in real-time
- ❌ Wait for deployment to complete
- ❌ Trigger webhooks or external services
- ❌ Check live website status

---

## 📋 Knowledge & Context

### Training Data
- **Knowledge Cutoff:** January 31, 2025
- **Can answer:** Historical facts, APIs as of Jan 2025, general tech knowledge
- **Cannot reliably answer:** Events after Jan 2025, current API changes, breaking changes
- **Workaround:** Web search (if enabled) or owner provides current information

### Session Context
- **Token Budget:** ~190,000 tokens per session
- **Conversation History:** Full (can see everything in this chat)
- **File System:** Access to `/home/claude/statute-app` repository only
- **No Memory Between Sessions:** Each new session is fresh (no persistent memory unless enabled)

### Limitations
- ❌ Cannot see GUI/screenshots without upload
- ❌ Cannot execute long-running tasks
- ❌ Cannot maintain persistent state across sessions
- ❌ Cannot access files outside the working directory

---

## 🔧 MCP Connectors Available

### GitHub (OAuth Configured)
- ✅ `mcp__Github__push_files` — **Push commits to main**
- ✅ `mcp__Github__create_or_update_file` — Create/update single files
- ✅ `mcp__Github__get_file_contents` — Read files
- ✅ `mcp__Github__create_pull_request` — Create PRs
- ✅ `mcp__Github__list_commits` — List commits
- ✅ `mcp__Github__search_code` — Search code

### Google Drive (if configured)
- 🔒 Would allow reading/writing Google Drive files
- 🔒 Not currently set up for this project

### Other MCP Services
- 🔒 Supabase, Cloudflare, Gmail (if connected)
- 🔒 Available if owner enables them

---

## 📌 What Owner Must Do

### Critical Path
1. **Deploy to production:**
   - Option A: Run `git push origin main` locally (I can't do this without local credentials)
   - Option B: I can push via GitHub MCP connector (need OAuth secret keys configured) ← **READY**

2. **Verify deployment:**
   - Owner must open browser and test: https://statuteapp.github.io/
   - Owner must check GitHub Actions logs

3. **Retest R38–R45:**
   - Owner must test on phone/browser (I can't do this)
   - Owner must confirm no regressions

### Decisions Owner Must Make
- Crime UI: Popup vs report panel?
- Street works: Show in Today tab?
- Council meetings approach: Option A, B, or C?
- Which councils to expand to?

---

## 💡 Typical Workflow

### What Happens in This Session
1. Claude: Write code, create tests, write documentation
2. Claude: Commit locally (via bash in `/home/claude/statute-app`)
3. Claude: Push to GitHub (via MCP GitHub connector + OAuth)
4. Owner: Verifies deployment
5. Owner: Retests features
6. Owner: Makes decisions on next priorities

### What Doesn't Work
- Claude: Cannot `git push` locally without credentials in this environment
- Claude: Cannot test live APIs (403 Forbidden due to network policy)
- Claude: Cannot verify website is actually live
- Owner: Cannot ask Claude to do something requiring external API calls or network access

### Workarounds
- **For Git Push:** Use GitHub MCP (OAuth configured) ← Done ✅
- **For API Testing:** Deploy first, then owner verifies live
- **For Decisions:** Owner provides input, Claude implements
- **For Secrets:** Store in GitHub (Actions secrets, not code)

---

## 🎯 For Next Session

### How to Start
```
1. Claude: Ask "What do I need to know about the Statute app?"
2. Owner: Can share links, decisions, new requirements
3. Claude: Has access to:
   - Full conversation history (if in same chat)
   - /home/claude/statute-app/ (local repo)
   - GitHub via MCP (read/write with OAuth)
   - Documentation created in this session
```

### If Memory Is Enabled
- Claude will have access to summaries from past sessions
- No need to re-explain context
- Can pick up where we left off

### If Memory Is Disabled (Default)
- Claude starts fresh each session
- Read this file (CLAUDE-CAPABILITIES.md)
- Check TRACKER.md for current status
- Check ROADMAP.md for next priorities

---

## 📊 Capabilities Matrix

| Task | Local? | MCP? | Web? | Notes |
|------|--------|------|------|-------|
| Write code | ✅ | - | - | Can write Python, JS, etc. |
| Run tests | ✅ | - | - | Can run pytest, bash tests |
| Git commit | ✅ | - | - | Can commit locally |
| Git push | ❌ | ✅ | - | Use MCP GitHub connector |
| API testing | ❌ | - | - | 403 Forbidden (network policy) |
| GitHub read | ✅ | ✅ | - | Can use both methods |
| Verify live site | ❌ | - | ❌ | Owner must verify |
| Write docs | ✅ | - | - | Full markdown support |
| Create pull requests | - | ✅ | - | Via GitHub MCP |
| Make decisions | - | - | - | Owner decides, Claude implements |

---

## 🚨 When Claude Gets Stuck

If I say "I cannot do this because...", check:

1. **Network error?** → Deploy first, verify after (not before)
2. **Credential error?** → Use MCP connector or owner handles locally
3. **File not found?** → Check working directory is `/home/claude/statute-app/`
4. **Token limit?** → Summarize chat or start new session
5. **API blocked?** → Wait for production deployment (GitHub Pages has no blocks)

---

## ✨ Bottom Line

**I am good at:**
- Writing & testing code
- Creating documentation
- Planning architecture
- Pushing code via GitHub MCP (when OAuth is configured)
- Debugging & problem-solving

**I need owner for:**
- Final verification (testing live site)
- Making design decisions
- Providing feedback
- Testing on real device/browser
- Handling anything requiring user authentication

**For Statute App specifically:**
- ✅ All R48 code is complete and tested locally
- ✅ Can push to GitHub via MCP (ready to deploy)
- ⏳ Owner: git push or approve MCP push
- ⏳ Owner: Verify deployment on live site
- ⏳ Owner: Retest R38–R45
- ⏳ Owner: Provide feedback on next priorities

---

**tl;dr:** I can develop, test, document, and push code. I can't test live APIs (network blocked) or verify deployment (not a browser). Owner must verify the site is actually working and make decisions. We work well together because we each handle what we're good at.