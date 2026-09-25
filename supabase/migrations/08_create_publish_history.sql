DO $$ BEGIN
    CREATE TYPE public.publish_status AS ENUM ('pending', 'success', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;


CREATE TABLE IF NOT EXISTS public.publish_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID NOT NULL REFERENCES public.variants(id) ON DELETE CASCADE,
    platform public.social_platform NOT NULL,
    

    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    
    status public.publish_status NOT NULL DEFAULT 'pending',
    

    response_payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    
    attempt_count INT NOT NULL DEFAULT 1,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),


    CONSTRAINT unique_successful_variant_publish UNIQUE (variant_id)
);

CREATE INDEX IF NOT EXISTS idx_publish_history_idempotency_key ON public.publish_history(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_publish_history_variant_id ON public.publish_history(variant_id);


ALTER TABLE public.publish_history ENABLE ROW LEVEL SECURITY;


CREATE POLICY "Service role full access on publish_history"
ON public.publish_history
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Users can view publish history of their own posts"
ON public.publish_history
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.variants v
        JOIN public.raw_posts p ON v.post_id = p.id
        WHERE v.id = public.publish_history.variant_id
          AND p.user_id = auth.uid()
    )
);