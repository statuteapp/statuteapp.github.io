# Ready to Deploy R47-R48 to Production

## 🚀 Deployment Command

```bash
git push origin main
```

**That's it.** GitHub Actions handles everything else.

---

## What Happens Next (Automatically)

1. **Feed workflow** (5 mins)
   - Builds measures.json with live environmental data
   - Runs 15 tests (all passing)
   - Commits to main

2. **Pages workflow** (2 mins)
   - Deploys to GitHub Pages
   - Site goes live

3. **Total time:** ~7-10 minutes

---

## Verify Deployment (10 mins)

### Step 1: Check GitHub Actions
https://github.com/statuteapp/statuteapp.github.io/actions
- Look for "Build feed" workflow
- Should show ✅ Success

### Step 2: Visit Live Site
https://statuteapp.github.io/
- Click "Today" tab
- Should see environmental measures:
  - Air quality (Defra)
  - Pollen (UKHSA)
  - River level (Environment Agency)
  - Water status (Environment Agency)
  - UV Index (pending)
  - Humidity (if available)

### Step 3: Check Console
- Open F12 (Developer Tools)
- Should see: `Loading measures from ./measures.json`
- No errors

### Step 4: Retest
- Tap crime pins (should show "Police street-level crime" label)
- Check food alerts
- Check status page
- Verify map works

---

## What's Changed in R47-R48

### R47: Crime Labels
- Crime pins now labeled "Police street-level crime"
- Status page updated

### R48: Environmental Measures
- **New:** Today tab shows live environmental data
- **New:** measures.json updates hourly
- **New:** 15 automated tests
- **Improved:** All APIs work for any UK location

---

## If Something Goes Wrong

### Measures.json Not Updating
1. Wait 15 minutes (hourly build)
2. Check GitHub Actions logs
3. See BUGS.md for troubleshooting

### API Data Not Showing
1. Check network tab (F12)
2. Confirm measures.json exists
3. Should contain data

### Rollback (If Needed)
```bash
git revert <commit-sha>
git push origin main
```

---

## Owner Checklist

- [ ] Run `git push origin main`
- [ ] Wait 5-10 minutes for deployment
- [ ] Visit https://statuteapp.github.io/
- [ ] Click "Today" tab
- [ ] Verify environmental measures visible
- [ ] Check crime pins have new label
- [ ] Retest other features (no regressions)
- [ ] Confirm no console errors (F12)

---

**Ready? Run:** `git push origin main`

**Questions?** See DEPLOYMENT.md for full details.