# Cursor Perplexity Configuration Fix

## ✅ Completed Actions

### 1. Fixed Settings Files
- **Project Settings**: `.cursor/settings.json`
- **Global Settings**: `~/Library/Application Support/Cursor/User/settings.json`

Both files now have:
- ✅ Correct baseURL: `https://api.perplexity.ai/v1` (with `/v1` suffix)
- ✅ Your Perplexity API key configured
- ✅ Model names: `sonar-pro` and `sonar` (verified working via API)
- ✅ Default model: `sonar-pro`
- ✅ Local models disabled to prevent conflicts
- ✅ Cloud routing disabled

### 2. Verified API Connectivity
- ✅ `sonar-pro` works via direct API calls
- ✅ `sonar` works via direct API calls
- ❌ `pplx-sonar-pro` and `pplx-sonar` do NOT work (removed from config)

### 3. Removed Conflicting Models
- ✅ Removed Ollama models (`llama-3.1-8b-instruct`, `llama-3.1-70b-instruct`)
- ✅ Removed invalid Perplexity models (`sonar-reasoning-pro`, `sonar-deep-research`)
- ✅ Disabled local models (`enableLocalModels: false`)

## 🔍 Current Issue: Client-Side Validation

If Cursor is still showing "The model sonar does not work with your current plan or api key", this is likely **client-side validation** blocking the model before it even makes an API call.

## 🛠️ Next Steps to Diagnose

### Step 1: Check Developer Tools Console
1. Open Cursor
2. Press `Cmd+Shift+P` (or `Ctrl+Shift+P` on Windows/Linux)
3. Type "Toggle Developer Tools" and select it
4. Go to the **Console** tab
5. Try to select `sonar-pro` as your model
6. Look for errors in the console

**What to look for:**
- Error codes (401, 403, 404)
- Error messages mentioning "model", "plan", or "api key"
- Network requests to Perplexity API (check if they're even being made)

### Step 2: Check Network Tab
1. In Developer Tools, go to **Network** tab
2. Filter by "perplexity" or "api"
3. Try selecting the model again
4. Check if requests are being made to `https://api.perplexity.ai/v1/chat/completions`

**What to look for:**
- Are requests being made? (If not, it's client-side blocking)
- What's the response status code?
- What's the response body?

### Step 3: Use Cursor UI Settings
1. Go to **Cursor → Settings → Models** (or `Cmd+,` → Models)
2. Verify:
   - ✅ "Override OpenAI Base URL" is **enabled**
   - ✅ Base URL is set to: `https://api.perplexity.ai/v1`
   - ✅ API Key is set (should show as configured)
3. Try adding models manually:
   - Click "Add Custom Model"
   - Name: `sonar-pro`
   - Provider: OpenAI
   - Model ID: `sonar-pro`
   - Base URL: `https://api.perplexity.ai/v1`

### Step 4: Check SQLite Database
The API key is stored in Cursor's internal database. Verify it's correct:

```bash
sqlite3 ~/Library/Application\ Support/Cursor/User/globalStorage/state.vscdb \
  "SELECT key, value FROM ItemTable WHERE key = 'cursorAuth/openAIKey';"
```

Should show your Perplexity API key.

## 🎯 Possible Solutions

### Solution 1: Restart Cursor
After updating settings, **completely quit and restart Cursor**:
1. Quit Cursor (`Cmd+Q`)
2. Wait 5 seconds
3. Reopen Cursor
4. Try selecting `sonar-pro` again

### Solution 2: Clear Cursor Cache
If restart doesn't work, clear Cursor's cache:

```bash
# Backup first!
cp -r ~/Library/Application\ Support/Cursor/User/globalStorage/state.vscdb \
  ~/Library/Application\ Support/Cursor/User/globalStorage/state.vscdb.backup

# Then restart Cursor (it will rebuild cache)
```

### Solution 3: Use Custom Model in UI
If settings.json isn't working, use the UI:
1. Cursor → Settings → Models
2. Enable "Override OpenAI Base URL"
3. Add custom model manually
4. Select it from the dropdown

### Solution 4: Check for Cursor Pro Credits Conflict
If you have Cursor Pro, it might be trying to use Cursor's credits instead of your API key:
1. Check if "Use Cursor Credits" is enabled
2. Disable it if you want to use your own API key
3. Verify the API key is being used (check Network tab)

## 📋 Diagnostic Script

Run the diagnostic script to verify API connectivity:

```bash
cd /path/to/matchfly-pseo
node diagnose_cursor_config.js
```

This will:
- Test API connectivity
- Verify model names work
- Check your configuration files
- Provide recommendations

## 🔑 Key Findings

1. **API Works**: `sonar-pro` and `sonar` work perfectly via direct API calls
2. **Settings Correct**: Both project and global settings are configured correctly
3. **No Conflicts**: Ollama and invalid models removed
4. **Issue**: Likely client-side validation in Cursor blocking models before API call

## 📝 Error Codes Reference

- **401**: Invalid API key (check your key)
- **403**: Model not available for your plan (check Perplexity subscription)
- **404**: Model not found (wrong model name)
- **Client-side**: Cursor blocking before API call (check Developer Tools)

## 🆘 If Still Not Working

1. **Check Developer Tools Console** for exact error
2. **Check Network Tab** to see if API calls are being made
3. **Try UI Settings** instead of settings.json
4. **Restart Cursor** completely
5. **Contact Cursor Support** with:
   - Exact error message from Console
   - Network request details
   - Your Cursor version
   - Your OS version

---

**Last Updated**: 2026-01-15
**Status**: Configuration fixed, awaiting Cursor restart and Developer Tools check
