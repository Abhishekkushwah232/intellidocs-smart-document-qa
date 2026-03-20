"""Supabase Python clients: service role for storage; anon for optional auth helpers."""
from supabase import create_client

from app.core.config import settings

supabase_storage = create_client(settings.supabase_url, settings.supabase_service_key)
supabase_auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)

