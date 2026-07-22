module.exports = {
  apps: [
    {
      name: 'backend',
      cwd: '/var/www/backend',
      script: '.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      env: {
        PATH: '/var/www/backend/.venv/bin:' + process.env.PATH
      }
    }
  ]
}