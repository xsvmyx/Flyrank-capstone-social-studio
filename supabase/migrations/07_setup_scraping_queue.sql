-- =====================================================================
-- 1. CREATE THE PGMQ QUEUE FOR SCRAPING
-- =====================================================================
SELECT pgmq.create('scraping_jobs');

-- =====================================================================
-- 2. SCRAPING REQUESTS TABLE
--    (OPTIONAL BUT RECOMMENDED FOR TRACEABILITY)
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.scraping_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS & Grants for the table
ALTER TABLE public.scraping_requests ENABLE ROW LEVEL SECURITY;
GRANT ALL ON public.scraping_requests TO postgres, service_role;
GRANT SELECT, INSERT ON public.scraping_requests TO authenticated;

-- =====================================================================
-- 3. TRIGGER FUNCTION: PUSHES A JOB INTO 'scraping_jobs' ON EACH INSERT
-- =====================================================================
CREATE OR REPLACE FUNCTION enqueue_scraping_job()
RETURNS TRIGGER 
SECURITY DEFINER
SET search_path = public, pgmq
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pgmq.send(
        queue_name => 'scraping_jobs',
        msg => jsonb_build_object(
            'scraping_request_id', NEW.id,
            'user_id', NEW.user_id,
            'url', NEW.url,
            'event', 'scraping.requested',
            'created_at', NEW.created_at
        )
    );
    RETURN NEW;
END;
$$;

-- Install the trigger on public.scraping_requests
DROP TRIGGER IF EXISTS trigger_enqueue_scraping
ON public.scraping_requests;

CREATE TRIGGER trigger_enqueue_scraping
    AFTER INSERT ON public.scraping_requests
    FOR EACH ROW
    EXECUTE FUNCTION enqueue_scraping_job();





CREATE POLICY "Users can insert their own scraping requests"
ON public.scraping_requests
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);


CREATE POLICY "Users can view their own scraping requests"
ON public.scraping_requests
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);