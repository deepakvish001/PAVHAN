import { useEffect, useState } from 'react'
import { listItems, onOutboxChange, watchConnection } from '../lib/outbox'

/**
 * How many captures are waiting to be sent.
 *
 * Mounted once at the top of the app, this is also what starts the outbox
 * listening for the connection coming back — so a listing recorded in a field
 * sends itself the moment the phone finds a tower, without the artisan having
 * to remember to open anything.
 */
export function useOutboxCount() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let alive = true
    const read = () => listItems()
      .then((rows) => { if (alive) setCount(rows.filter((r) => r.status !== 'sent').length) })
      .catch(() => {})
    read()
    const off = onOutboxChange(read)
    const stop = watchConnection()
    return () => { alive = false; off(); stop() }
  }, [])

  return count
}
