CREATE TYPE public.social_platform AS ENUM (
    'linkedin',
    'twitter',
    'instagram',
    'facebook'
);


CREATE TYPE public.variant_status AS ENUM (
    'pending',      
    'completed',    
    'failed',       
    'published'     
);


CREATE TABLE IF NOT EXISTS public.posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.raw_posts(id) ON DELETE CASCADE,
    platform public.social_platform NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    status public.variant_status NOT NULL DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),


    CONSTRAINT unique_post_platform UNIQUE (post_id, platform)
);


CREATE INDEX idx_posts_post_id ON public.posts(post_id);
CREATE INDEX idx_posts_platform_status ON public.posts(platform, status);


CREATE TRIGGER update_posts_modtime
    BEFORE UPDATE ON public.posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;


CREATE POLICY "Service Role full access on posts"
    ON public.posts
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);