# Supabase Database Setup Guide

This directory contains everything needed to set up Supabase as the database and storage backend for the GNB Dog Image Generation Backend.

## 📁 Files

- `supabase_setup.sql` - Supabase-optimized DDL script with triggers, RLS, and real-time features
- `create_tables.sql` - Legacy PostgreSQL DDL script (for direct PostgreSQL)
- `setup_database.sh` - Legacy setup script for PostgreSQL
- `README.md` - This documentation

## 🚀 Quick Setup with Supabase

### Step 1: Create Supabase Project

1. **Go to [Supabase Dashboard](https://app.supabase.com)**
2. **Create a new project**
3. **Note down your project details:**
   - Project URL: `https://your-project-id.supabase.co`
   - API Keys (from Settings > API)
   - Database password (from Settings > Database)

### Step 2: Run SQL Setup

1. **Open Supabase SQL Editor** in your dashboard
2. **Copy and paste** the contents of `supabase_setup.sql`
3. **Execute** the script to create tables, views, and functions

### Step 3: Configure Storage Bucket

1. **Go to Storage** in Supabase Dashboard
2. **Create a new bucket** named `gnb-dog-images`
3. **Set bucket to public** (for generated images)
4. **Configure policies** as needed

### Step 4: Update Environment Variables

Create a `.env` file with your Supabase credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Direct Database Connection
DATABASE_URL=postgresql+asyncpg://postgres:your_db_password@db.your-project.supabase.co:5432/postgres

# Storage Configuration
SUPABASE_STORAGE_BUCKET=gnb-dog-images
USE_SUPABASE_STORAGE=true

# Azure OpenAI (Required)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_dalle_deployment
```

## 📊 Supabase Database Schema

### Enhanced Features

Supabase provides additional features over plain PostgreSQL:

- **Real-time subscriptions** for live updates
- **Automatic REST APIs** for all tables
- **Row Level Security (RLS)** for data protection
- **Built-in authentication** (optional)
- **Edge functions** for serverless compute
- **Built-in storage** with CDN

### Tables

#### `image_generations`
Enhanced with Supabase-specific features:

- **Automatic timestamps** with triggers
- **JSONB support** for Azure metadata
- **Real-time updates** capability
- **REST API** auto-generated

#### `generation_statistics`
Daily aggregated analytics with:

- **Automatic timestamp updates**
- **Real-time statistics view**
- **REST API access**

### Views

#### `daily_generation_summary`
Daily statistics with success rates and performance metrics.

#### `recent_generations`
Last 100 generation requests with duration calculations.

#### `live_statistics` (New!)
Real-time statistics for current day - perfect for dashboards.

### Functions

#### `get_system_statistics()`
Returns JSON with current system statistics:

```sql
SELECT get_system_statistics();
```

#### `cleanup_old_generations(days)`
Clean up old records:

```sql
SELECT cleanup_old_generations(30);
```

#### `update_daily_statistics(date)`
Update statistics for a specific date:

```sql
SELECT update_daily_statistics(CURRENT_DATE);
```

## 🔄 Real-time Features

### Subscribe to Changes

You can subscribe to real-time changes in your frontend:

```javascript
// Subscribe to new image generations
const subscription = supabase
  .channel('image-generations')
  .on('postgres_changes', 
    { event: 'INSERT', schema: 'public', table: 'image_generations' },
    (payload) => console.log('New generation:', payload)
  )
  .subscribe()
```

### Live Statistics

Monitor live statistics with the `live_statistics` view:

```javascript
// Get real-time statistics
const { data } = await supabase
  .from('live_statistics')
  .select('*')
  .single()
```

## 🗄️ Supabase Storage Integration

### Bucket Configuration

The `supabase_storage.py` service provides:

- **Image upload/download**
- **Signed URLs** for private access
- **File management**
- **Storage statistics**

### Usage Example

```python
from services.supabase_storage import storage_service

# Upload an image
file_path, public_url = await storage_service.upload_image(
    image_bytes=image_data,
    filename="dog.jpg",
    folder="generations"
)

# Download an image
image_bytes = await storage_service.download_image(file_path)

# Generate signed URL
signed_url = await storage_service.generate_signed_url(
    file_path=file_path,
    expires_in=3600  # 1 hour
)
```

## 🔐 Security & Permissions

### Row Level Security (RLS)

RLS policies are prepared in the SQL script but commented out since we don't use authentication:

```sql
-- Enable RLS if you add user authentication later
ALTER TABLE image_generations ENABLE ROW LEVEL SECURITY;
```

### API Access

- **Anon key**: For public read access to statistics
- **Service role key**: For full database access from backend
- **Custom policies**: Configure as needed for your use case

## 📈 Analytics & Monitoring

### Built-in Analytics

Supabase provides built-in analytics:

1. **Database usage** in Dashboard
2. **API request** monitoring
3. **Real-time** active connections
4. **Storage usage** tracking

### Custom Queries

Access your data via SQL Editor:

```sql
-- Recent activity
SELECT * FROM recent_generations LIMIT 10;

-- Daily stats
SELECT * FROM daily_generation_summary ORDER BY generation_date DESC LIMIT 7;

-- Live statistics
SELECT * FROM live_statistics;

-- System overview
SELECT get_system_statistics();
```

## 🚀 Production Considerations

### Performance

- **Connection pooling**: Configured automatically
- **Read replicas**: Available in Pro plans
- **Global CDN**: For storage and API
- **Edge functions**: For low-latency compute

### Backup & Recovery

- **Automatic backups**: Daily backups included
- **Point-in-time recovery**: Available in Pro plans
- **Data export**: Full database export available

### Scaling

- **Automatic scaling**: Database scales with usage
- **Compute instances**: Upgradeable as needed
- **Storage limits**: Generous limits per plan

## 🆘 Troubleshooting

### Common Issues

1. **Connection failed**
   - Check Supabase project is active
   - Verify API keys are correct
   - Ensure database password is accurate

2. **SQL execution errors**
   - Check SQL syntax in Supabase editor
   - Verify table permissions
   - Review error logs in Dashboard

3. **Storage upload fails**
   - Check bucket exists and is public
   - Verify storage policies
   - Ensure sufficient storage quota

### Debugging Tools

- **Supabase Dashboard**: Monitor all services
- **SQL Editor**: Execute queries directly
- **Logs**: View real-time logs
- **API**: Test endpoints directly

### Migration from PostgreSQL

If migrating from plain PostgreSQL:

1. **Export data**: `pg_dump your_old_db > backup.sql`
2. **Run Supabase setup**: Execute `supabase_setup.sql`
3. **Import data**: Use SQL Editor to import your data
4. **Update connection**: Switch to Supabase connection string

---

## 🌟 Benefits of Supabase

- **All-in-one platform**: Database + Storage + Auth + API
- **Real-time capabilities**: Live updates out of the box
- **Developer experience**: Excellent dashboard and tooling
- **Scalability**: Automatic scaling and optimization
- **Cost-effective**: Generous free tier + reasonable pricing

**Ready to start generating images?** Your Supabase backend is now configured and ready! 🎉 