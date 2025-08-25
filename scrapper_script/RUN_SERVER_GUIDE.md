# How to Run the Google Maps Scraper Server

## 🚀 Quick Start Options

You have **3 ways** to run the server:

### Option 1: Simple Command Line (Recommended for Testing)

1. **Set your environment variables** (create a `.env` file or set them manually):
```bash
# Windows Command Prompt
set SUPABASE_URL=https://your-project.supabase.co
set SUPABASE_ANON_KEY=your-supabase-anon-key
set ADMIN_ID=your-uuid-from-supabase-auth
set SERVER_HOST=0.0.0.0
set SERVER_PORT=5000
set N8N_WEBHOOK_URL=http://localhost:5678/webhook/job-completion

# Or create a .env file with these values
```

2. **Run the server**:
```bash
python main.py
```

### Option 2: GUI Application (User-Friendly)

1. **Run the GUI**:
```bash
python gui_app.py
```

2. **Configure in the GUI**:
   - Go to Configuration tab
   - Fill in all your details (Supabase URL, API Key, Admin UUID, etc.)
   - Save configuration
   - Go to Server Control tab
   - Click "Start Server"

### Option 3: Compile to Single EXE (For Distribution)

1. **Install PyInstaller**:
```bash
pip install pyinstaller
```

2. **Run the build script**:
```bash
python build_exe.py
```

This will create a single executable file that includes everything.

## 🔧 UUID Admin ID Setup

Since you changed your database to use UUIDs, here's what you need to do:

### 1. Update Your Database

Your admins table should now look like this:
```sql
CREATE TABLE public.admins (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  name character varying NOT NULL,
  status character varying DEFAULT 'active',
  supported_keywords ARRAY DEFAULT '{}',
  max_concurrent_jobs integer DEFAULT 3,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT admins_pkey PRIMARY KEY (id)
);
```

### 2. Create Your Admin Record

In your Supabase dashboard, run:
```sql
INSERT INTO public.admins (id, email, name, status, supported_keywords, max_concurrent_jobs) 
VALUES ('your-uuid-here', 'scraper@yourdomain.com', 'Your Server Name', 'active', '{}', 3);
```

**To get your UUID**: If you're using Supabase Auth, you can get the user UUID from the auth.users table, or generate one:
```sql
SELECT gen_random_uuid(); -- This generates a new UUID
```

### 3. Update Your scrape_jobs Table

Make sure your scrape_jobs table has the new UUID field:
```sql
ALTER TABLE public.scrape_jobs 
ADD COLUMN assigned_to_uuid uuid;

ALTER TABLE public.scrape_jobs 
ADD CONSTRAINT scrape_jobs_assigned_to_uuid_fkey 
FOREIGN KEY (assigned_to_uuid) REFERENCES public.admins(id);
```

## 🧪 Testing Your Setup

1. **Test the UUID functionality**:
```bash
python test_uuid_server.py
```

2. **Test the server health**:
```bash
curl http://localhost:5000/health
```

3. **Test a scraping job**:
```bash
curl -X POST http://localhost:5000/scrape-single \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 123,
    "area_id": 1,
    "admin_id": "your-uuid-here",
    "search_term": "restaurants",
    "area_name": "Lahore, Pakistan",
    "max_results": 5
  }'
```

## 📝 Environment Variables You Need

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://abc123.supabase.co` |
| `SUPABASE_ANON_KEY` | Your Supabase anonymous key | `eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...` |
| `ADMIN_ID` | Your admin UUID (not integer anymore!) | `550e8400-e29b-41d4-a716-446655440000` |
| `SERVER_HOST` | Server host (use 0.0.0.0 for all interfaces) | `0.0.0.0` |
| `SERVER_PORT` | Server port | `5000` |
| `N8N_WEBHOOK_URL` | Your N8N webhook URL | `http://localhost:5678/webhook/job-completion` |

## 🐛 Troubleshooting

### "ValueError: invalid literal for int() with base 10"
- This means you're still using the old code that tries to convert admin_id to integer
- Make sure you're using the updated `database_manager.py` file

### "Admin not found" error
- Make sure you have an admin record in your database with the correct UUID
- Check that your `ADMIN_ID` environment variable matches exactly

### "Database connection failed"
- Verify your `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Check your internet connection
- Make sure your Supabase project is active

### Server won't start
- Check if port 5000 is already in use: `netstat -an | findstr :5000`
- Try a different port by setting `SERVER_PORT=5001`

## 🏗️ Building Single EXE

If you want to create a single executable file:

1. **Make sure everything works first** with `python main.py`
2. **Install build dependencies**:
```bash
pip install pyinstaller
```
3. **Run the build**:
```bash
python build_exe.py
```

The executable will be created in the `dist/` folder.

## 📊 Monitoring

- Use the GUI application for real-time monitoring
- Check server logs for detailed information
- Monitor your Supabase database for job status updates
- Use the `/health` endpoint to check server status

## 🔄 N8N Integration

Your N8N workflow should send requests like this:
```json
{
  "job_id": 123,
  "area_id": 456,
  "admin_id": "550e8400-e29b-41d4-a716-446655440000",
  "search_term": "restaurants",
  "area_name": "New York, NY",
  "max_results": 20
}
```

Note that `admin_id` is now a UUID string, not an integer!
