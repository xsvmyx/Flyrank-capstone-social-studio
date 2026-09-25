CREATE TABLE IF NOT EXISTS public.scraping_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


ALTER TABLE public.scraping_requests ENABLE ROW LEVEL SECURITY;
GRANT ALL ON public.scraping_requests TO postgres, service_role;
GRANT SELECT, INSERT ON public.scraping_requests TO authenticated;

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



CREATE OR REPLACE FUNCTION enqueue_scraping_job()
RETURNS TRIGGER 
SECURITY DEFINER
SET search_path = public, pgmq
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pgmq.send(
        queue_name => 'background_jobs',
        msg => jsonb_build_object(
            'event', 'scraping.requested',
            'payload', jsonb_build_object(
                'scraping_request_id', NEW.id,
                'user_id', NEW.user_id,
                'url', NEW.url,
                'created_at', NEW.created_at
            )
        )
    );
    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trigger_enqueue_scraping ON public.scraping_requests;

CREATE TRIGGER trigger_enqueue_scraping
    AFTER INSERT ON public.scraping_requests
    FOR EACH ROW
    EXECUTE FUNCTION enqueue_scraping_job();