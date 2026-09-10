CREATE POLICY "Users can manage their own variants"
    ON public.variants
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.raw_posts
            WHERE public.raw_posts.id = public.variants.post_id
            AND public.raw_posts.user_id = auth.uid()
        )
    );