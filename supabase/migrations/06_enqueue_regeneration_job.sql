CREATE OR REPLACE FUNCTION public.enqueue_regeneration_job(p_post_id UUID)
RETURNS BIGINT
SECURITY DEFINER
SET search_path = public, pgmq
LANGUAGE plpgsql
AS $$
DECLARE
    v_msg_id BIGINT;
BEGIN
    SELECT pgmq.send(
        'raw_posts_jobs', 
        jsonb_build_object('post_id', p_post_id)
    ) INTO v_msg_id;
    
    RETURN v_msg_id;
END;
$$;


GRANT EXECUTE ON FUNCTION public.enqueue_regeneration_job(UUID) TO authenticated, service_role;