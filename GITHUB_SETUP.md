# GitHub Repository Setup Guide for SmartCharge

This guide walks you through setting up your SmartCharge integration as a GitHub repository and making it installable via HACS.

## Step 1: Create GitHub Repository

### 1.1 Create New Repository

1. Go to [github.com/new](https://github.com/new)
2. Enter repository details:
   - **Repository name**: `smartcharge`
   - **Description**: `SmartCharge - EV Charging Station Monitor for Home Assistant`
   - **Visibility**: Public (required for HACS)
   - **Initialize with README**: No (we'll use our existing README.md)

3. Click **Create repository**

### 1.2 Clone to Your Local Machine

```bash
# Clone the empty repository
git clone https://github.com/iandresari/smartcharge.git
cd smartcharge
```

## Step 2: Prepare Integration Files

### 2.1 Copy Integration to Repository

Copy all files from `enbw_charging/` to the `smartcharge/` repository:

```bash
# From HomeAssistant addons folder
cp -r enbw_charging/* /path/to/smartcharge/
```

### 2.2 Structure Should Look Like:

```
smartcharge/
├── .github/
│   └── workflows/
│       └── hassfest.yaml
├── smartcharge/           # This is the custom_components folder contents
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
│   ├── translations/
│   └── requirements.txt
├── hacs.json
├── README.md
├── LICENSE
├── QUICKSTART.md
├── GETTING_STARTED.md
└── (other documentation files)
```

**Important**: The integration code should be in a `smartcharge/` subdirectory, NOT at the root.

### 2.3 Create Directory Structure

```bash
cd smartcharge
mkdir -p smartcharge/translations
# Move integration files to smartcharge/ subdirectory
```

## Step 3: GitHub Repository Files

### 3.1 Files Already Created

✅ `hacs.json` - HACS configuration  
✅ `.github/workflows/hassfest.yaml` - CI/CD pipeline  

### 3.2 Create `.gitignore`

Yours is already included, just ensure it's at the root:

```bash
# Make sure .gitignore is at repository root
```

## Step 4: Git Configuration

### 4.1 Configure Git

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 4.2 Add and Commit Files

```bash
# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: SmartCharge integration"

# Push to GitHub
git push -u origin main
```

## Step 5: HACS Registration

### 5.1 Register with HACS

1. Fork the [HACS repository](https://github.com/hacs/default) (optional but recommended)
2. Visit the HACS Configuration UI or:
   - Go to [HACS Store](https://hacs.xyz/)
   - Click "New Repository"
   - Enter: `https://github.com/iandresari/smartcharge`
   - Select category: **Integration**
   - Click "Install"

### 5.2 Wait for HACS Approval

- HACS validates your repository automatically
- Check the workflow runs at: `https://github.com/iandresari/smartcharge/actions`
- Expect approval within 24-48 hours if all requirements are met

## Step 6: Verify Setup

### 6.1 Check GitHub Actions

Go to your repository and click **Actions** tab:

```
✅ Validate with HACS
✅ Hassfest  
✅ Check code style
✅ Lint
```

All should pass (or have green checkmarks).

### 6.2 Test Installation

#### Option A: HACS Store

1. Open Home Assistant
2. Go to: **HACS → Integrations**
3. Search for **"SmartCharge"**
4. Click **Install**
5. Restart Home Assistant

#### Option B: Manual from GitHub

```bash
# SSH into Home Assistant
mkdir -p /config/custom_components/smartcharge

# Clone from GitHub
git clone https://github.com/iandresari/smartcharge /config/custom_components/smartcharge/smartcharge

# Restart Home Assistant
```

Then create the integration as normal.

## Step 7: Create Release

### 7.1 Create a Git Tag

```bash
git tag -a v1.0.1 -m "SmartCharge v1.0.1"
git push origin v1.0.1
```

### 7.2 Create GitHub Release

1. Go to your repository
2. Click **Releases** 
3. Click **Create a new release**
4. Tag version: `v1.0.1`
5. Title: `SmartCharge v1.0.1`
6. Description: Copy from [CHANGELOG.md](../CHANGELOG.md)
7. Click **Publish release**

## File Requirements for HACS

✅ `manifest.json` - Integration metadata  
✅ `hacs.json` - HACS configuration  
✅ `README.md` - Repository documentation  
✅ `LICENSE` - License file (must be MIT, Apache, etc.)  
✅ Integration code in `smartcharge/` subdirectory  

### HACS Validation Checklist

- [ ] Repository is public
- [ ] `manifest.json` exists with valid domain
- [ ] `hacs.json` exists with correct configuration
- [ ] `README.md` exists
- [ ] `LICENSE` file is present
- [ ] Integration folder is `smartcharge/` (matches domain)
- [ ] No obvious errors in code

## Environment Setup

### Install Linting Tools

```bash
pip install black flake8 isort mypy
```

### Run Linting Locally

```bash
# Run all checks
black smartcharge/
isort smartcharge/
flake8 smartcharge/
mypy smartcharge/
```

## Troubleshooting

### HACS Shows "Requirements Not Met"

- Check `hacs.json` format
- Verify repository is public
- Ensure folder is named `smartcharge`

### GitHub Actions Failing

- Check workflow logs at: Actions → [workflow name]
- Common issues:
  - Python version too old
  - Missing dependencies
  - Code style violations (run black locally)

### Installation Not Working

- Check custom_components folder structure
- Verify file permissions (chmod 755)
- Check Home Assistant logs for errors

## Next Steps

1. Update `README.md` with your GitHub profile links
2. Update `manifest.json` with your username
3. Monitor GitHub Actions for validation
4. Share with community!

## Useful Links

- [HACS Documentation](https://hacs.xyz/)
- [Home Assistant Custom Component Development](https://developers.home-assistant.io/docs/creating_integration_repo)
- [GitHub Actions Documentation](https://docs.github.com/actions)

## Repository URLs (Replace with Your Details)

```
Repository: https://github.com/iandresari/smartcharge
Issues: https://github.com/iandresari/smartcharge/issues
Releases: https://github.com/iandresari/smartcharge/releases
HACS Install: https://github.com/iandresari/smartcharge
```

---

**Status**: Ready for GitHub deployment  
**Current Version**: 1.0.1  
**License**: MIT
