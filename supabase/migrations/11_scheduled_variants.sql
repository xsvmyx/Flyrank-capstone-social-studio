
ALTER TABLE public.variants 
ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;


CREATE INDEX IF NOT EXISTS idx_variants_scheduled 
ON public.variants(scheduled_at) 
WHERE status = 'scheduled';



CREATE OR REPLACE FUNCTION public.pgmq_send(
    queue_name text, 
    msg jsonb, 
    delay integer DEFAULT 0
)
RETURNS bigint 
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN pgmq.send(queue_name, msg, delay);
END;
$$;