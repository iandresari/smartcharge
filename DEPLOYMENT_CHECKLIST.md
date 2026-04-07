# SmartCharge GitHub Deployment Checklist

Complete this checklist to deploy SmartCharge to GitHub and make it available via HACS.

## Phase 1: Pre-GitHub Setup ✅

- [x] Integration code complete (30+ files)
- [x] All documentation written (13 files)
- [x] Domain renamed to "smartcharge"
- [x] manifest.json updated with HACS fields
- [x] const.py updated with new DOMAIN
- [x] hacs.json created for HACS compatibility
- [x] GitHub Actions workflow created (hassfest.yaml)
- [x] Setup guides created (GITHUB_SETUP.md, HACS_INSTALLATION.md)

## Phase 2: GitHub Repository Creation

### 2.1 Create Repository

- [ ] Go to https://github.com/new
- [ ] Name: `smartcharge`
- [ ] Description: `SmartCharge - EV Charging Station Monitor for Home Assistant`
- [ ] Make it **Public** (required for HACS)
- [ ] Initialize without README
- [ ] Click **Create repository**

**Repository URL**: `https://github.com/YOUR-USERNAME/smartcharge`

### 2.2 Clone Repository

```bash
git clone https://github.com/YOUR-USERNAME/smartcharge.git
cd smartcharge
```

## Phase 3: Add Integration Files

### 3.1 Copy Files

All integration files should be organized:

```
smartcharge/
├── smartcharge/                 # ← Integration folder
│   ├── __init__.py
│   ├── config_flow.py
│   ├── const.py
│   ├── coordinator.py
│   ├── sensor.py
│   ├── binary_sensor.py
│   ├── services.py
│   ├── manifest.json
│   ├── strings.json
│   ├── py.typed
│   ├── requirements.txt
│   └── translations/
├── .github/
│   └── workflows/
│       └── hassfest.yaml
├── hacs.json                    # ← HACS configuration
├── README.md                    # ← GitHub README (from GITHUB_README.md)
├── QUICKSTART.md
├── GETTING_STARTED.md
├── CONFIGURATION.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                      # ← MIT License
└── .gitignore
```

### 3.2 Verify Files

- [ ] `smartcharge/` folder contains all integration files
- [ ] `hacs.json` is at repository root
- [ ] `.github/workflows/hassfest.yaml` exists
- [ ] `README.md` has correct content (from GITHUB_README.md)
- [ ] `LICENSE` file exists
- [ ] `.gitignore` configured properly

## Phase 4: Configure Git & Commit

### 4.1 Configure Git

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 4.2 Add Files

```bash
git add .
```

### 4.3 Create Initial Commit

```bash
git commit -m "Initial commit: SmartCharge integration v1.0.1"
```

### 4.4 Push to GitHub

```bash
git push -u origin main
```

- [ ] Push successful
- [ ] Files visible on GitHub

## Phase 5: Verify GitHub Setup

### 5.1 Check Repository Files

- [ ] Files appear on GitHub web interface
- [ ] Folder structure is correct
- [ ] README.md displays properly
- [ ] LICENSE is readable

### 5.2 Check GitHub Actions

Navigate to: `https://github.com/YOUR-USERNAME/smartcharge/actions`

- [ ] Workflows triggered automatically
- [ ] Hassfest validation passed ✅
- [ ] HACS validation passed ✅
- [ ] Code style checks passed ✅
- [ ] Linting passed ✅

**View workflow results**: Click on the workflow run to see details

## Phase 6: Create First Release

### 6.1 Create Tags

```bash
git tag -a v1.0.1 -m "SmartCharge v1.0.1 - Initial Release"
git push origin v1.0.1
```

### 6.2 Create GitHub Release

1. Go to: `https://github.com/YOUR-USERNAME/smartcharge/releases`
2. Click **Create a new release**
3. Fill in:
   - **Tag version**: `v1.0.1`
   - **Release title**: `SmartCharge v1.0.1`
   - **Description**: Copy from [CHANGELOG.md](./CHANGELOG.md)
   - **Pre-release**: unchecked
4. Click **Publish release**

- [ ] Release created successfully
- [ ] Release visible on GitHub

## Phase 7: HACS Registration

### 7.1 Update Repository References

In multiple files, replace `YOUR-USERNAME` with your GitHub username:

1. **hacs.json** - Update repository URL
2. **manifest.json** - Update documentation URLs
3. **README.md** - Update all links (if used as GitHub README)
4. **GITHUB_SETUP.md** - Update example URLs

```bash
# Search & replace in all files
# OLD: https://github.com/YOUR-USERNAME/smartcharge
# NEW: https://github.com/your-actual-username/smartcharge
```

### 7.2 Register with HACS

Two options:

**Option A: Automatic (Wait for HACS Indexing)**
- HACS automatically discovers and indexes public repositories
- Wait 24-48 hours for repository to appear in HACS Store
- Then searchable in HACS Integrations

**Option B: Manual Repository Addition**
1. Open Home Assistant
2. HACS → Integrations
3. Click menu icon (⋯)
4. Select **Custom repositories**
5. Add: `https://github.com/YOUR-USERNAME/smartcharge`
6. Category: **Integration**
7. Click **Create**

- [ ] Repository registered with HACS (automatic or manual)
- [ ] Appears in HACS Integrations list

## Phase 8: Test Installation

### 8.1 HACS Installation Test

1. In Home Assistant, open HACS
2. Go to **Integrations**
3. Search for **"SmartCharge"**
4. Click **Install**
5. Restart Home Assistant
6. Go to Settings → Devices & Services
7. Create new integration → SmartCharge
8. Complete 5-step setup wizard

- [ ] Installation successful
- [ ] Entities created and visible
- [ ] No errors in Home Assistant logs

### 8.2 Manual Installation Test (Optional)

```bash
# SSH into Home Assistant
ssh root@homeassistant.local

# Clone to custom_components
mkdir -p /config/custom_components/smartcharge
git clone https://github.com/YOUR-USERNAME/smartcharge /tmp/smartcharge_test
cp -r /tmp/smartcharge_test/smartcharge/* /config/custom_components/smartcharge/

# Restart Home Assistant and verify
```

- [ ] Manual installation works
- [ ] Integration appears in integrations list

## Phase 9: Documentation Updates

### 9.1 GitHub README

- [ ] Replace `GITHUB_README.md` content with main `README.md` on GitHub
- [ ] Update all `YOUR-USERNAME` references
- [ ] Verify badges display correctly
- [ ] Update all repository links

### 9.2 Installation Guides

- [ ] [HACS_INSTALLATION.md](./HACS_INSTALLATION.md) - Complete and accurate
- [ ] [GITHUB_SETUP.md](./GITHUB_SETUP.md) - Complete and accurate
- [ ] [GETTING_STARTED.md](./GETTING_STARTED.md) - References GitHub repo

### 9.3 Configuration Guides

- [ ] [QUICKSTART.md](./QUICKSTART.md) - Updated if needed
- [ ] [CONFIGURATION.md](./CONFIGURATION.md) - Updated if needed

## Phase 10: Community Sharing

### 10.1 Share with Community

- [ ] Post on [Home Assistant Community Forum](https://community.home-assistant.io/)
- [ ] Include:
  - Repository link
  - Feature summary
  - Installation instructions
  - Example configuration

### 10.2 Monitoring

- [ ] Monitor GitHub Issues for bug reports
- [ ] Respond to issues promptly
- [ ] Create fixes and release updates
- [ ] Maintain CHANGELOG.md
- [ ] Create releases for significant updates

## Deployment Commands (Quick Reference)

```bash
# 1. Initial setup
git clone https://github.com/YOUR-USERNAME/smartcharge.git
cd smartcharge

# 2. Copy integration files (ensure smartcharge/ folder exists)
# Copy all integration files into smartcharge/ subdirectory

# 3. Configure and commit
git config user.name "Your Name"
git config user.email "your.email@example.com"
git add .
git commit -m "Initial commit: SmartCharge integration v1.0.1"

# 4. Push to GitHub
git push -u origin main

# 5. Create release tag
git tag -a v1.0.1 -m "SmartCharge v1.0.1"
git push origin v1.0.1

# 6. Create release on GitHub
# Manual step: Create release through GitHub web interface
```

## Troubleshooting

### Issue: HACS Validation Fails

**Solution**:
1. Check GitHub Actions workflow for error details
2. Common issues:
   - Wrong domain name (should be "smartcharge")
   - Missing hacs.json
   - Invalid manifest.json JSON
3. Fix errors locally and push again

### Issue: Repository Not Appearing in HACS

**Solution**:
1. Ensure repository is **public**
2. Wait 24-48 hours for HACS indexing
3. Manually add repository in HACS:
   - HACS → Integrations → ⋯ → Custom repositories
   - Add: https://github.com/YOUR-USERNAME/smartcharge

### Issue: Installation Fails

**Solution**:
1. Check Home Assistant logs for errors
2. Verify file permissions (755 on Unix)
3. Ensure folder structure matches requirements
4. Try manual installation first

### Issue: Entities Not Creating

**Solution**:
1. Check manifest.json for issues
2. Verify Python version 3.9+
3. Check Home Assistant logs
4. Try creating configuration again

## Success Criteria

✅ **Deployment Complete When:**

1. GitHub repository created and public
2. All files pushed to GitHub main branch
3. GitHub Actions workflows passing (all green checkmarks)
4. hacs.json and manifest.json valid
5. Repository appears in HACS Integrations
6. Installation via HACS successful
7. Integration configurable in Home Assistant
8. Entities created and functioning
9. Documentation complete and accurate
10. First release (v1.0.1) created

## Next Steps After Deployment

1. **Gather Feedback**: Monitor issues and community feedback
2. **Bug Fixes**: Create patch releases as needed
3. **Features**: Plan v1.1.0 with additional features
4. **Documentation**: Keep docs updated with new features
5. **Community**: Engage with users and contributors

---

## Support & Resources

- **HACS Docs**: https://hacs.xyz/
- **Home Assistant Docs**: https://developers.home-assistant.io/
- **Integration Repo Template**: https://github.com/home-assistant/integration_blueprint
- **GitHub Actions**: https://docs.github.com/actions

---

**Status**: Ready for GitHub Deployment  
**Version**: 1.0.1  
**License**: MIT  
**Created**: 2024
