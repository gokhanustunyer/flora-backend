# Quick Setup Guide - Environment Configuration

This guide will help you configure the GNB Dog Image Generation Backend using the `.env` file.

## 🚀 Quick Start (Minimal Configuration)

For basic functionality, you only need Azure OpenAI credentials:

1. **Copy the environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` and configure the required Azure OpenAI settings:**
   ```env
   AZURE_OPENAI_API_KEY=your_actual_api_key_here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=your_dalle_deployment_name
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

✅ **You now have basic image generation working!**

## 🔧 Configuration Levels

### Level 1: Basic (Azure AI Only)
**Required settings:**
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT` 
- `AZURE_OPENAI_DEPLOYMENT_NAME`

**Available features:**
- Core image generation endpoint (`POST /api/v1/generate`)
- Health check endpoint (`GET /api/v1/health`)
- Basic error handling and logging

### Level 2: Add Database (Request Tracking)
**Additional settings:**
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gnb_dog_images
```

**New features unlocked:**
- Request tracking and logging
- Generation history storage
- Enhanced analytics and monitoring

```

**New features unlocked:**
- Persistent image storage
- Secure download URLs
- Enhanced image management
- Full production capabilities

## 🎯 Feature Matrix

| Feature | Level 1 | Level 2 | Level 3 |
|---------|---------|---------|---------|
| Image Generation | ✅ | ✅ | ✅ |
| Health Check | ✅ | ✅ | ✅ |
| Request Tracking | ❌ | ✅ | ✅ |
| Persistent Storage | ❌ | ❌ | ✅ |
| Secure URLs | ❌ | ❌ | ✅ |

## 🛠️ Advanced Configuration

### Performance Tuning
```env
AI_GENERATION_TIMEOUT=30
MAX_IMAGE_DIMENSION=1024
DATABASE_POOL_SIZE=5
```

### Development Settings
```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
RELOAD_ON_CHANGE=true
```

## 🔍 Troubleshooting

### Check Feature Status
Visit `http://localhost:3001/` to see which features are enabled.

### Common Issues

1. **"Database features disabled"**
   - Add `DATABASE_URL` to your `.env` file
   - Ensure PostgreSQL is running

2. **"Storage features disabled"**
   - Add `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY` to your `.env`

### Health Check
Visit `http://localhost:3001/health` for detailed service status.

## 🚀 Production Deployment

For production, ensure you have:

```env
# Production settings
DEBUG_MODE=false
RELOAD_ON_CHANGE=false
LOG_LEVEL=INFO

# Performance
DATABASE_POOL_SIZE=10
AI_GENERATION_TIMEOUT=30

# Security
CORS_ORIGINS=["https://yourdomain.com"]
```

## 📝 Example .env Files

### Minimal Development (Just Azure AI)
```env
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=dalle-3
DEBUG_MODE=true
```

### Full Development (All Features)
```env
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=dalle-3

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gnb_dog_images

AZURE_STORAGE_ACCOUNT_NAME=mystorageaccount
AZURE_STORAGE_ACCOUNT_KEY=storage_key_here

DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Production
```env
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_ENDPOINT=https://prod-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=dalle-3

DATABASE_URL=postgresql+asyncpg://user:secure_password@prod-db:5432/gnb_dog_images

AZURE_STORAGE_ACCOUNT_NAME=prodstorage
AZURE_STORAGE_ACCOUNT_KEY=secure_storage_key

CORS_ORIGINS=["https://yourdomain.com"]
DEBUG_MODE=false
LOG_LEVEL=INFO
DATABASE_POOL_SIZE=10
```

---

🎉 **That's it!** The application will automatically detect which features to enable based on your `.env` configuration. 