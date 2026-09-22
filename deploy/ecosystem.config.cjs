module.exports = {
  apps: [{
    name: "alkaas",
    cwd: "/home/root/projects/alkaas",
    script: "wsgi.py",
    interpreter: "/home/root/projects/alkaas/venv/bin/python",
    env: {
      HOST: "127.0.0.1",
      PORT: "4041",
      FLASK_DEBUG: "0",
      FLASK_ENV: "production"
    },
    autorestart: true,
    watch: false,
    time: true,
    max_memory_restart: "500M",
    kill_timeout: 10000
  }]
};
