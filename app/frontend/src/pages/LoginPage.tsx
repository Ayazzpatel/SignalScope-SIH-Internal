import { FlaskConical } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { AuthCard } from '../components/auth/AuthCard.tsx'
import { Alert } from '../components/ui/Alert.tsx'
import { Button } from '../components/ui/Button.tsx'
import { PasswordField, TextField } from '../components/ui/Field.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import { useHealth } from '../hooks/useHealth.ts'
import { NO_ERRORS, toFormErrors, withoutFieldError, type FormErrors } from '../lib/forms.ts'
import { safeNext } from '../lib/navigation.ts'

const DEMO = { email: 'demo@signalscope.dev', password: 'SignalScope#2026' }

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const health = useHealth()
  const next = safeNext(params.get('next'))

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setErrors(NO_ERRORS)
    try {
      await login(email, password, remember)
      navigate(next, { replace: true })
    } catch (err) {
      setErrors(toFormErrors(err, ['email', 'password']))
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      eyebrow="Access · sign in"
      title="Welcome back"
      subtitle="Sign in to reach your scan history from any device."
      footer={
        <>
          New to SignalScope?{' '}
          <Link to={`/signup?next=${encodeURIComponent(next)}`} className="font-medium text-signal hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="grid gap-5">
        {errors.form && <Alert tone="error">{errors.form}</Alert>}

        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => {
            setEmail(e.target.value)
            setErrors((prev) => withoutFieldError(prev, 'email'))
          }}
          error={errors.fields.email}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => {
            setPassword(e.target.value)
            setErrors((prev) => withoutFieldError(prev, 'password'))
          }}
          error={errors.fields.password}
        />

        <label className="flex items-center gap-2.5 text-sm text-mute">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="size-4 accent-signal"
          />
          Keep me signed in for 30 days
        </label>

        <Button type="submit" loading={submitting} className="w-full">
          Sign in
        </Button>
      </form>

      {health.kind === 'online' && health.data.demo_accounts && (
        <div className="mt-7 rounded-sm border border-dashed border-line-strong p-4">
          <p className="flex items-center gap-2 text-sm font-medium">
            <FlaskConical className="size-4 text-signal" aria-hidden />
            Demo account available
          </p>
          <p className="mt-1.5 font-mono text-xs text-mute">
            {DEMO.email} · {DEMO.password}
          </p>
          <Button
            type="button"
            variant="ghost"
            className="mt-3 px-3 py-2 text-[13px]"
            onClick={() => {
              setEmail(DEMO.email)
              setPassword(DEMO.password)
              setErrors(NO_ERRORS)
            }}
          >
            Fill in demo credentials
          </Button>
        </div>
      )}
    </AuthCard>
  )
}
