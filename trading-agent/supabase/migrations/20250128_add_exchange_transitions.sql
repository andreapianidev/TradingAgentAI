-- Migration: Add Exchange Transition System
-- Description: Adds tables and settings for safe exchange transitions between Alpaca and Hyperliquid
-- Date: 2025-01-28

-- ============================================================
-- 1. CREATE trading_exchange_transitions TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS trading_exchange_transitions (
  -- Primary key
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Transition configuration
  transition_strategy TEXT NOT NULL CHECK (transition_strategy IN ('IMMEDIATE', 'PROFITABLE', 'WAIT_PROFIT', 'MANUAL')),
  status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),

  -- Exchange information
  from_exchange TEXT NOT NULL,  -- 'alpaca' or 'hyperliquid'
  to_exchange TEXT NOT NULL,

  -- Progress tracking
  total_positions INT NOT NULL DEFAULT 0,
  positions_closed INT NOT NULL DEFAULT 0,
  positions_remaining INT NOT NULL DEFAULT 0,
  positions_in_profit INT NOT NULL DEFAULT 0,
  positions_in_loss INT NOT NULL DEFAULT 0,

  -- Financial metrics
  total_pnl DECIMAL(20, 8),
  total_pnl_pct DECIMAL(10, 4),

  -- Timestamps
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  last_check_at TIMESTAMPTZ,

  -- Manual override fields
  manual_override_required BOOLEAN DEFAULT FALSE,
  manual_override_approved BOOLEAN DEFAULT FALSE,
  manual_override_by TEXT,
  manual_override_at TIMESTAMPTZ,

  -- Error handling
  error_count INT DEFAULT 0,
  last_error TEXT,
  retry_after TIMESTAMPTZ,

  -- Structured data
  position_ids TEXT[] DEFAULT '{}',
  transition_log JSONB DEFAULT '[]',

  -- Trading mode
  trading_mode TEXT NOT NULL DEFAULT 'paper' CHECK (trading_mode IN ('paper', 'live'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transitions_status ON trading_exchange_transitions(status);
CREATE INDEX IF NOT EXISTS idx_transitions_strategy ON trading_exchange_transitions(transition_strategy);
CREATE INDEX IF NOT EXISTS idx_transitions_created ON trading_exchange_transitions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transitions_mode ON trading_exchange_transitions(trading_mode);

-- Add RLS policies for trading_exchange_transitions
ALTER TABLE trading_exchange_transitions ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Allow service role full access to transitions"
ON trading_exchange_transitions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Allow authenticated users to read transitions
CREATE POLICY "Allow authenticated users to read transitions"
ON trading_exchange_transitions
FOR SELECT
TO authenticated
USING (true);

COMMENT ON TABLE trading_exchange_transitions IS 'Tracks exchange transitions from Alpaca to Hyperliquid and vice versa';

-- ============================================================
-- 2. MODIFY trading_positions TABLE
-- ============================================================

-- Add exchange tracking fields
ALTER TABLE trading_positions
ADD COLUMN IF NOT EXISTS exchange TEXT DEFAULT 'alpaca',
ADD COLUMN IF NOT EXISTS in_transition BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS transition_id UUID REFERENCES trading_exchange_transitions(id) ON DELETE SET NULL;

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_positions_exchange ON trading_positions(exchange);
CREATE INDEX IF NOT EXISTS idx_positions_in_transition ON trading_positions(in_transition) WHERE in_transition = TRUE;
CREATE INDEX IF NOT EXISTS idx_positions_transition_id ON trading_positions(transition_id) WHERE transition_id IS NOT NULL;

COMMENT ON COLUMN trading_positions.exchange IS 'Exchange where position was opened (alpaca or hyperliquid)';
COMMENT ON COLUMN trading_positions.in_transition IS 'Whether position is currently being transitioned to another exchange';
COMMENT ON COLUMN trading_positions.transition_id IS 'Reference to active transition if position is being transitioned';

-- ============================================================
-- 3. ADD TRANSITION SETTINGS
-- ============================================================

-- Insert transition configuration settings
INSERT INTO trading_settings (setting_key, setting_value, description, category)
VALUES
  ('transition_strategy', '"WAIT_PROFIT"', 'Strategy for exchange transitions: IMMEDIATE, PROFITABLE, WAIT_PROFIT, MANUAL', 'trading'),
  ('transition_timeout_hours', '72', 'Maximum hours to wait for profitable close before emergency close', 'risk'),
  ('transition_emergency_loss_pct', '-10.0', 'Emergency close if total loss exceeds this percentage', 'risk'),
  ('transition_sl_tighten_pct', '50.0', 'How much to tighten stop loss in PROFITABLE strategy (percentage reduction)', 'risk')
ON CONFLICT (setting_key) DO UPDATE SET
  setting_value = EXCLUDED.setting_value,
  description = EXCLUDED.description,
  category = EXCLUDED.category,
  updated_at = NOW();

-- ============================================================
-- 4. CREATE HELPER FUNCTIONS
-- ============================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_trading_exchange_transitions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS trigger_update_trading_exchange_transitions_updated_at ON trading_exchange_transitions;
CREATE TRIGGER trigger_update_trading_exchange_transitions_updated_at
  BEFORE UPDATE ON trading_exchange_transitions
  FOR EACH ROW
  EXECUTE FUNCTION update_trading_exchange_transitions_updated_at();

-- ============================================================
-- VERIFICATION QUERIES (commented out - run manually to verify)
-- ============================================================

/*
-- Verify table created
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'trading_exchange_transitions'
ORDER BY ordinal_position;

-- Verify indexes created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'trading_exchange_transitions';

-- Verify trading_positions columns added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'trading_positions'
AND column_name IN ('exchange', 'in_transition', 'transition_id');

-- Verify settings added
SELECT setting_key, setting_value, description, category
FROM trading_settings
WHERE setting_key LIKE 'transition%';
*/
