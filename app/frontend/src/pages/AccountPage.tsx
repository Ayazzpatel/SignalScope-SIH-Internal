import { Database, Download, KeyRound, LogOut, Monitor, ShieldCheck, Trash2, TriangleAlert, UserRound } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { PasswordStrength } from '../components/auth/PasswordStrength.tsx'
import { Alert } from '../components/ui/Alert.tsx'
import { Button } from '../components/ui/Button.tsx'
import { PasswordField, TextField } from '../components/ui/Field.tsx'
import { Switch } from '../components/ui/Switch.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import { api } from '../lib/api.ts'
import { NO_ERRORS, toFormErrors, withoutFieldError, type FormErrors } from '../lib/forms.ts'
import { formatDate, timeAgo } from '../lib/navigation.ts'
import { RETENTION_OPTIONS } from '../lib/presentation.ts'
import type { RetentionDays, SessionInfo, User } from '../types/auth.ts'

export function AccountPage() {
  const { user } = useAuth()
  if (!user) return null // RequireAuth guarantees a user; this keeps TypeScript honest.

  return (
    <div className="mx-auto grid max-w-3xl animate-rise gap-5">
      <header className="mb-3">
        <span className="label">Console · account & security</span>
        <h1 className="mt-3 text-[clamp(36px,5vw,56px)] leading-none font-semibold tracking-[-0.04em]">
          Your <em className="display-em">account</em>
        </h1>
        <p className="mt-3 text-mute">Manage your profile, password and signed-in devices.</p>
      </header>
      <ProfileSection user={user} />
      <PrivacySection user={user} />
      <PasswordSection email={user.email} />
      <SessionsSection />
      <DangerZone />
    </div>
  )
}

function Section({ icon, title, description, children, id, danger = false }: {
  icon: ReactNode
  title: string
  description: string
  children: ReactNode
  id?: string
  danger?: boolean
}) {
  return (
    <section id={id} className={`panel scroll-mt-24 p-5 sm:p-6 ${danger ? 'border-ai/30' : ''}`}>
      <h2 className="flex items-center gap-2.5 text-lg font-semibold tracking-tight">
        {icon}
        {title}
      </h2>
      <p className="mt-1 text-sm text-mute">{description}</p>
      <div className="mt-6">{children}</div>
    </section>
  )
}

// ------------------------------------------------------------------ profile

function ProfileSection({ user }: { user: User }) {
  const { setUser } = useAuth()
  const [displayName, setDisplayName] = useState(user.display_name)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS)
  const [saved, setSaved] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setErrors(NO_ERRORS)
    setSaved(false)
    try {
      setUser(await api.auth.updateProfile({ display_name: displayName }))
      setSaved(true)
    } catch (err) {
      setErrors(toFormErrors(err, ['display_name']))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section icon={<UserRound className="size-5 text-signal" aria-hidden />} title="Profile" description="How you appear in SignalScope.">
      <form onSubmit={onSubmit} className="grid gap-5">
        {errors.form && <Alert tone="error">{errors.form}</Alert>}
        {saved && <Alert tone="success">Profile updated.</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Display name"
            value={displayName}
            maxLength={80}
            required
            onChange={(e) => setDisplayName(e.target.value)}
            error={errors.fields.display_name}
          />
          <TextField label="Email" value={user.email} disabled readOnly />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="flex items-center gap-3 text-sm text-mute">
            <span className="rounded-sm border border-signal/40 px-1.5 py-1 font-mono text-[10.5px] leading-none tracking-widest text-signal uppercase">
              {user.role}
            </span>
            Member since {formatDate(user.created_at)}
          </p>
          <Button type="submit" loading={saving} disabled={displayName.trim() === user.display_name}>
            Save changes
          </Button>
        </div>
      </form>
    </Section>
  )
}

// ------------------------------------------------------------------ privacy

function SettingRow({ title, description, children }: { title: string; description: ReactNode; children: ReactNode }) {
  return (
    <div className="grid gap-3 border-b border-line py-4 first:pt-0 last:border-b-0 last:pb-0 sm:grid-cols-[1fr_auto] sm:items-center sm:gap-8">
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-0.5 text-[13px] text-mute">{description}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2 sm:justify-end">{children}</div>
    </div>
  )
}

function PrivacySection({ user }: { user: User }) {
  const { setUser } = useAuth()
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)

  const run = async (key: string, action: () => Promise<string | null>) => {
    setBusy(key)
    setMessage(null)
    try {
      const done = await action()
      if (done) setMessage({ tone: 'success', text: done })
    } catch (err) {
      setMessage({ tone: 'error', text: toFormErrors(err, []).form ?? 'Something went wrong.' })
    } finally {
      setBusy(null)
    }
  }

  const savePreference = (key: string, body: Parameters<typeof api.account.updatePreferences>[0]) =>
    run(key, async () => {
      setUser(await api.account.updatePreferences(body))
      return null
    })

  const exportData = () =>
    run('export', async () => {
      const data = await api.account.exportData()
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `signalscope-export-${new Date().toISOString().slice(0, 10)}.json`
      link.click()
      URL.revokeObjectURL(url)
      return 'Export downloaded.'
    })

  const clearHistory = () =>
    run('clear', async () => {
      const { deleted } = await api.scans.removeAll()
      setConfirmClear(false)
      return `Deleted ${deleted} scan${deleted === 1 ? '' : 's'} and their files.`
    })

  return (
    <Section
      id="privacy"
      icon={<Database className="size-5 text-signal" aria-hidden />}
      title="Privacy & data"
      description="Guests leave no trace. Signed-in scans save the result; images only if you choose."
    >
      {message && (
        <div className="mb-4">
          <Alert tone={message.tone}>{message.text}</Alert>
        </div>
      )}
      <SettingRow
        title="Keep images by default"
        description="When off, only the verdict, heat-map and metadata are saved. You can still choose per scan."
      >
        <Switch
          on={user.save_images_default}
          disabled={busy === 'images'}
          onChange={(next) => void savePreference('images', { save_images_default: next })}
        >
          {user.save_images_default ? 'On' : 'Off'}
        </Switch>
      </SettingRow>
      <SettingRow title="Keep scans for" description="Older scans and their files are deleted automatically.">
        <label className="sr-only" htmlFor="retention">
          Keep scans for
        </label>
        <select
          id="retention"
          value={user.retention_days ?? 'forever'}
          disabled={busy === 'retention'}
          onChange={(e) =>
            void savePreference('retention', {
              retention_days: e.target.value === 'forever' ? null : (Number(e.target.value) as RetentionDays),
            })
          }
          className="rounded-md border border-line-strong bg-ink px-2.5 py-2 text-sm focus:border-signal focus:outline-none"
        >
          {RETENTION_OPTIONS.map((option) => (
            <option key={option.label} value={option.value ?? 'forever'}>
              {option.label}
            </option>
          ))}
        </select>
      </SettingRow>
      <SettingRow title="Export my data" description="Account, sessions and every saved result, as a JSON file.">
        <Button variant="ghost" loading={busy === 'export'} onClick={() => void exportData()}>
          <Download className="size-4" aria-hidden />
          Download export
        </Button>
      </SettingRow>
      <SettingRow title="Delete scan history" description="Removes every saved scan, heat-map and image. Your account stays.">
        {confirmClear ? (
          <>
            <Button variant="quiet" onClick={() => setConfirmClear(false)} disabled={busy === 'clear'}>
              Cancel
            </Button>
            <Button variant="danger" loading={busy === 'clear'} onClick={() => void clearHistory()}>
              Yes, delete all
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={() => setConfirmClear(true)}>
            <Trash2 className="size-4" aria-hidden />
            Delete history
          </Button>
        )}
      </SettingRow>
    </Section>
  )
}

// ------------------------------------------------------------------ danger zone

function DangerZone() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.account.deleteAccount(password)
      await logout()
      navigate('/', { replace: true })
    } catch (err) {
      const errors = toFormErrors(err, ['password'])
      setError(errors.fields.password ?? errors.form)
      setBusy(false)
    }
  }

  return (
    <Section
      danger
      icon={<TriangleAlert className="size-5 text-ai" aria-hidden />}
      title="Delete account"
      description="Permanently deletes your account, sessions, scans and files. This cannot be undone."
    >
      {open ? (
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <PasswordField
            label="Confirm with your password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              setError(null)
            }}
            error={error}
          />
          <div className="flex gap-2">
            <Button type="button" variant="quiet" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" variant="danger" loading={busy} disabled={!password}>
              Delete forever
            </Button>
          </div>
        </form>
      ) : (
        <Button variant="danger" onClick={() => setOpen(true)}>
          Delete my account
        </Button>
      )}
    </Section>
  )
}

// ------------------------------------------------------------------ password

function PasswordSection({ email }: { email: string }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS)
  const [done, setDone] = useState<string | null>(null)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setDone(null)
    if (next !== confirm) {
      setErrors({ form: null, fields: { confirm: "Passwords don't match." } })
      return
    }
    setSaving(true)
    setErrors(NO_ERRORS)
    try {
      const { message } = await api.auth.changePassword({ current_password: current, new_password: next })
      setDone(message)
      setCurrent('')
      setNext('')
      setConfirm('')
    } catch (err) {
      setErrors(toFormErrors(err, ['current_password', 'new_password']))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section
      icon={<KeyRound className="size-5 text-signal" aria-hidden />}
      title="Password"
      description="Changing your password signs you out on every other device."
    >
      <form onSubmit={onSubmit} className="grid gap-5">
        {errors.form && <Alert tone="error">{errors.form}</Alert>}
        {done && <Alert tone="success">{done}</Alert>}
        <PasswordField
          label="Current password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(e) => {
            setCurrent(e.target.value)
            setErrors((prev) => withoutFieldError(prev, 'current_password'))
          }}
          error={errors.fields.current_password}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <PasswordField
            label="New password"
            autoComplete="new-password"
            required
            value={next}
            onChange={(e) => {
              setNext(e.target.value)
              setErrors((prev) => withoutFieldError(prev, 'new_password'))
            }}
            error={errors.fields.new_password}
            hint={next ? <PasswordStrength password={next} email={email} /> : undefined}
          />
          <PasswordField
            label="Confirm new password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => {
              setConfirm(e.target.value)
              setErrors((prev) => withoutFieldError(prev, 'confirm'))
            }}
            error={errors.fields.confirm}
          />
        </div>
        <div className="flex justify-end">
          <Button type="submit" loading={saving} disabled={!current || !next || !confirm}>
            Change password
          </Button>
        </div>
      </form>
    </Section>
  )
}

// ------------------------------------------------------------------ sessions

function SessionsSection() {
  const { logout, logoutEverywhere } = useAuth()
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [confirmAll, setConfirmAll] = useState(false)

  const load = useCallback(async () => {
    try {
      setSessions((await api.auth.sessions()).sessions)
      setError(null)
    } catch (err) {
      setError(toFormErrors(err, []).form)
    }
  }, [])

  useEffect(() => {
    // State is set only after the async fetch resolves, not synchronously in the effect.
    // oxlint-disable-next-line react/set-state-in-effect
    void load()
  }, [load])

  const revoke = async (session: SessionInfo) => {
    setBusyId(session.id)
    try {
      if (session.current) {
        await logout()
        navigate('/login', { replace: true })
        return
      }
      await api.auth.revokeSession(session.id)
      await load()
    } catch (err) {
      setError(toFormErrors(err, []).form)
    } finally {
      setBusyId(null)
    }
  }

  const signOutEverywhere = async () => {
    setBusyId('all')
    try {
      await logoutEverywhere()
      navigate('/login', { replace: true })
    } catch (err) {
      setError(toFormErrors(err, []).form)
      setBusyId(null)
    }
  }

  return (
    <Section
      icon={<ShieldCheck className="size-5 text-signal" aria-hidden />}
      title="Signed-in devices"
      description="If you don't recognise a device, revoke it and change your password."
    >
      {error && <Alert tone="error">{error}</Alert>}
      {sessions === null && !error && <p className="label">Loading sessions…</p>}

      {sessions && (
        <ul className="divide-y divide-line border-y border-line">
          {sessions.map((session) => (
            <li key={session.id} className="flex flex-wrap items-center gap-3 py-3.5">
              <Monitor className="size-5 shrink-0 text-faint" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2 font-medium">
                  {session.device}
                  {session.current && (
                    <span className="rounded-sm bg-signal px-1.5 py-1 font-mono text-[10px] leading-none font-semibold tracking-widest text-ink uppercase">
                      This device
                    </span>
                  )}
                </p>
                <p className="mt-0.5 font-mono text-[11.5px] text-faint">
                  {session.ip_address ?? 'unknown ip'} · signed in {formatDate(session.signed_in_at)} · active{' '}
                  {timeAgo(session.last_active_at)}
                </p>
              </div>
              <Button
                variant="ghost"
                loading={busyId === session.id}
                disabled={busyId !== null}
                onClick={() => void revoke(session)}
              >
                {session.current ? 'Sign out' : 'Revoke'}
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
        {confirmAll ? (
          <>
            <span className="text-sm text-mute">Sign out of every device, including this one?</span>
            <Button variant="quiet" onClick={() => setConfirmAll(false)} disabled={busyId === 'all'}>
              Cancel
            </Button>
            <Button variant="danger" loading={busyId === 'all'} onClick={() => void signOutEverywhere()}>
              <LogOut className="size-4" aria-hidden />
              Yes, sign out everywhere
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={() => setConfirmAll(true)} disabled={busyId !== null}>
            <LogOut className="size-4" aria-hidden />
            Sign out everywhere
          </Button>
        )}
      </div>
    </Section>
  )
}
