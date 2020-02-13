#include <linux/module.h>

MODULE_LICENSE("GPL");

#include <linux/fs.h>
#include <linux/device.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>
#include <linux/delay.h>

#define DRIVER_NAME "lat"

enum {
	MODE_SYSCALL = 0,
	MODE_KTHREAD = 1,
	MODE_INTERRUPT = 2,
};

struct lat_cmd {
	u64 ms;
	u64 mode;
};

struct mutex mutex;

struct lat_work {
	struct work_struct work;
	u64 ms;
} workdata;

/* not static to allow tracing */
void lat_delay(u64 ms, const char *where)
{
	pr_debug("lat: [worker] delaying by %llu ms\n", ms);
	mdelay(ms);
	pr_debug("lat: finished\n");
}

static void handle_work(struct work_struct *work)
{
	mutex_lock(&mutex);
	lat_delay(workdata.ms, "worker");
	mutex_unlock(&mutex);
}

u64 timer_ms;

static enum hrtimer_restart handle_timer(struct hrtimer *arg)
{
	lat_delay(timer_ms, "interrupt");

	return HRTIMER_NORESTART;
}

struct hrtimer timer;

static ssize_t lat_write(struct file *file, const char __user *buf, size_t size, loff_t *y)
{
	struct lat_cmd cmd;

	pr_debug("write\n");

	if (size != sizeof cmd)
		return -EINVAL;

	if (copy_from_user(&cmd, buf, sizeof cmd))
		return -EFAULT;

	if (cmd.ms > 1000)
		return -EINVAL;

	switch(cmd.mode) {
	case MODE_SYSCALL:
		lat_delay(cmd.ms, "syscall");
		break;
	case MODE_KTHREAD:
		mutex_lock(&mutex);
		pr_debug("lat: scheduling worker\n");
		workdata.ms = cmd.ms;
		schedule_work(&workdata.work);
		mutex_unlock(&mutex);
		break;
	case MODE_INTERRUPT:
		pr_debug("lat: scheduling timer\n");
		timer_ms = cmd.ms;
		hrtimer_cancel(&timer);
		hrtimer_start(&timer, ktime_set(0, 100 * 1000000LL), HRTIMER_MODE_REL_HARD);
		break;
	default:
		pr_debug("lat: unknown mode\n");
		return -EINVAL;
	}

	return sizeof cmd;
}

struct file_operations lat_fops = {
	.write = lat_write,
};

struct cdev cdev;
struct device dev;

int lat_init(void)
{
	int ret;

	device_initialize(&dev);
	cdev_init(&cdev, &lat_fops);
	dev.init_name = DRIVER_NAME;

	dev.class = class_create(THIS_MODULE, DRIVER_NAME);
	if (!dev.class) {
		return -1;
	}

	ret = alloc_chrdev_region(&dev.devt, 0, 1, DRIVER_NAME);
	if (ret) {
		class_destroy(dev.class);
		return ret;
	}

	ret = cdev_device_add(&cdev, &dev);
	if (ret) {
		unregister_chrdev_region(dev.devt, 1);
		class_destroy(dev.class);
		return ret;
	}

	mutex_init(&mutex);
	INIT_WORK(&workdata.work, handle_work);
	hrtimer_init(&timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL_HARD);
	timer.function = handle_timer;

	pr_debug("lat: initialized\n");

	return 0;
}

void lat_exit(void)
{
	cdev_device_del(&cdev, &dev);
	unregister_chrdev_region(dev.devt, 1);
	class_destroy(dev.class);
	cancel_work_sync(&workdata.work);
	hrtimer_cancel(&timer);
}

module_init(lat_init);
module_exit(lat_exit);

