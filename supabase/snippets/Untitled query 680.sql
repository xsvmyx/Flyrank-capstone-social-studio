CREATE POLICY "Users can delete publish history for their own variants"
ON public.publish_history
FOR DELETE
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