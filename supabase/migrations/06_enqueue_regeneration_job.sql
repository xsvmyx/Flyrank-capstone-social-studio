CREATE OR REPLACE FUNCTION public.enqueue_regeneration_job(p_post_id UUID)
RETURNS BIGINT
SECURITY DEFINER
SET search_path = public, pgmq
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_id UUID;
    v_msg_id BIGINT;
BEGIN
    
    SELECT user_id INTO v_user_id
    FROM public.raw_posts
    WHERE id = p_post_id;

    SELECT pgmq.send(
        'background_jobs', 
        jsonb_build_object(
            'event', 'raw_post.created',
            'payload', jsonb_build_object(
                'post_id', p_post_id,
                'user_id', v_user_id,
                'created_at', now()
            )
        )
    ) INTO v_msg_id;
    
    RETURN v_msg_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.enqueue_regeneration_job(UUID) TO authenticated, service_role;