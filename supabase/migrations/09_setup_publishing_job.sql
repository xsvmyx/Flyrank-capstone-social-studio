CREATE OR REPLACE FUNCTION enqueue_publish_job()
RETURNS TRIGGER 
SECURITY DEFINER
SET search_path = public, pgmq
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pgmq.send(
        queue_name => 'background_jobs',
        msg => jsonb_build_object(
            'event', 'variant.publish',
            'payload', jsonb_build_object(
                'history_id', NEW.id,
                'variant_id', NEW.variant_id,
                'idempotency_key', NEW.idempotency_key,
                'platform', NEW.platform,
                'created_at', NEW.created_at
            )
        )
    );
    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trigger_enqueue_publish ON public.publish_history;

CREATE TRIGGER trigger_enqueue_publish
    AFTER INSERT ON public.publish_history
    FOR EACH ROW
    EXECUTE FUNCTION enqueue_publish_job();