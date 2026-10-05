# Next Actions for Owner

## 📋 Immediate Actions (This Week)

### 1. Review Documentation (45 minutes)
Read in this order:
1. **DEPLOYMENT.md** (15 min) — How to deploy & verify
2. **COUNCIL-FLOWS-RESEARCH.md** (20 min) — Council data options
3. **ROADMAP.md** (15 min) — Feature roadmap & decisions needed

### 2. Make 5 Design Decisions (15 minutes)
From ROADMAP.md, decide on:
- [ ] Crime data: Popup or report panel?
- [ ] Street works: Show in Today tab?
- [ ] Council meetings: Option A (retry) or C (hybrid)?
- [ ] Which councils to start with: Slough + 2 others?
- [ ] App reorganisation: Map-first layout?

### 3. Deploy (Optional, When Ready)
If you want to deploy R48 now:
```bash
git push origin main
```
GitHub Actions will:
- Build measures.json (hourly schedule)
- Run tests (auto-validated)
- Deploy to GitHub Pages
- Go live within 5-10 minutes

### 4. Verify Deployment (20 minutes)
After pushing:
1. Open https://statuteapp.github.io/
2. Check Today tab (should show environmental measures)
3. Check browser console (no errors)
4. Retest a few features from R38-R45 (no regressions)

### 5. Retest R38-R45 (30 minutes)
After deployment, on your phone:
- [ ] Crime pins show "Police street-level crime" label
- [ ] Map pan/zoom works
- [ ] Food alerts visible
- [ ] Tap pins and panels open
- [ ] Status page shows sources

---

## 🎯 This Month (If Ready to Continue)

### Phase 2 (Based on Your Decisions)
1. **Implement crime UI** (1-2 days)
2. **Fix council meetings** (2-3 days for first council)
3. **Add location selector** (1 day)

### Phase 3 (Scaling)
1. Add more councils (parallel work)
2. Add planning data (if approved)
3. Performance optimizations

---

## 📞 Questions?

- **How to deploy?** → DEPLOYMENT.md
- **What changed?** → SESSION-SUMMARY.md or TRACKER.md
- **What's next?** → ROADMAP.md
- **What's broken?** → BUGS.md
- **How do I decide on council data?** → COUNCIL-FLOWS-RESEARCH.md

---

## ✅ Checklist for This Week

- [ ] Read DEPLOYMENT.md
- [ ] Read COUNCIL-FLOWS-RESEARCH.md
- [ ] Read ROADMAP.md
- [ ] Provide 5 design decisions (comment/email)
- [ ] Deploy (or confirm you want to wait)
- [ ] Retest R38–R45
- [ ] Provide feedback on next priorities

---

**When ready, just run: `git push origin main`**

(No other action needed — GitHub Actions handles the rest)

**Or wait and let me know your 5 decisions first.