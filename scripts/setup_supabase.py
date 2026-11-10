import psycopg2

DATABASE_URL = "postgresql://postgres.szxdgaxcviukffpiyezm:GPTCraftSupabase_2026_Key!@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

def setup():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # 1. Trigger to auto-confirm new users so email verification doesn't block local dev/testing
    cur.execute("""
    CREATE OR REPLACE FUNCTION public.auto_confirm_new_user()
    RETURNS TRIGGER AS $func$
    BEGIN
      NEW.email_confirmed_at = COALESCE(NEW.email_confirmed_at, now());
      NEW.confirmed_at = COALESCE(NEW.confirmed_at, now());
      RETURN NEW;
    END;
    $func$ LANGUAGE plpgsql SECURITY DEFINER;

    DROP TRIGGER IF EXISTS trigger_auto_confirm_new_user ON auth.users;
    CREATE TRIGGER trigger_auto_confirm_new_user
    BEFORE INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.auto_confirm_new_user();
    """)
    conn.commit()
    print("Auto-confirm trigger created!")

    # 2. Check public.plans to make sure free, super, hyper exist
    cur.execute("SELECT id, name FROM public.plans;")
    plans = cur.fetchall()
    print("Current plans:", plans)
    
    cur.execute("""
    INSERT INTO public.plans (id, name, price, description)
    VALUES 
      (1, 'free', 0, 'Free plan - 50 requests/day, 5,000 tokens'),
      (2, 'super', 15, 'Super plan - 500 requests/day, 50,000 tokens'),
      (3, 'hyper', 39, 'Hyper plan - 5,000 requests/day, 500,000 tokens')
    ON CONFLICT (id) DO UPDATE SET 
      name = EXCLUDED.name,
      price = EXCLUDED.price,
      description = EXCLUDED.description;
    """)
    conn.commit()
    print("Plans seeded/updated to match GPTCraft tiers (free, super, hyper)!")
    
    conn.close()

if __name__ == "__main__":
    setup()

def confirm_all_users():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("UPDATE auth.users SET email_confirmed_at = now() WHERE email_confirmed_at IS NULL;")
    conn.commit()
    print("Confirmed all unconfirmed auth.users:", cur.rowcount)
    conn.close()

confirm_all_users()

def create_user_sync_trigger():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
    CREATE OR REPLACE FUNCTION public.handle_new_user_sync()
    RETURNS TRIGGER AS $func$
    DECLARE
        v_name VARCHAR;
    BEGIN
        v_name := COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1));
        
        -- Check if user already exists by email
        IF EXISTS (SELECT 1 FROM public.users WHERE email = NEW.email) THEN
            UPDATE public.users 
            SET supabase_uid = NEW.id::text,
                updated_at = now()
            WHERE email = NEW.email;
        ELSE
            INSERT INTO public.users (email, name, supabase_uid, plan_id, is_active, created_at, updated_at)
            VALUES (NEW.email, v_name, NEW.id::text, 1, true, now(), now());
        END IF;
        RETURN NEW;
    END;
    $func$ LANGUAGE plpgsql SECURITY DEFINER;

    DROP TRIGGER IF EXISTS trigger_handle_new_user_sync ON auth.users;
    CREATE TRIGGER trigger_handle_new_user_sync
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_sync();
    """)
    conn.commit()
    print("User sync trigger between auth.users and public.users created!")
    conn.close()

create_user_sync_trigger()
