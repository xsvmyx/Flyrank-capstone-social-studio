CREATE TYPE public.social_platform AS ENUM (
    'linkedin',
    'twitter',
    'instagram',
    'facebook'
);

CREATE TYPE public.variant_status AS ENUM (
    'draft',
    'approved',
    'rejected',
    'published'
);

CREATE TABLE IF NOT EXISTS public.variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.raw_posts(id) ON DELETE CASCADE,
    platform public.social_platform NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    status public.variant_status NOT NULL DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_variant_post_platform UNIQUE (post_id, platform)
);

CREATE INDEX idx_variants_post_id
    ON public.variants(post_id);

CREATE INDEX idx_variants_platform_status
    ON public.variants(platform, status);

CREATE TRIGGER update_variants_modtime
    BEFORE UPDATE ON public.variants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE public.variants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role full access on variants"
    ON public.variants
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);